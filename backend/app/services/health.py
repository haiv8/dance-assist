from __future__ import annotations

import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.ai_coach import ai_provider_status
from app.services.task_store import task_store
from app.settings import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(
    key: str,
    status: str,
    title: str,
    message: str,
    suggestion: str,
    *,
    ok: bool | None = None,
    **extra: Any,
) -> dict[str, Any]:
    normalized = status if status in {"pass", "warn", "fail", "optional"} else "warn"
    return {
        "key": key,
        "status": normalized,
        "ok": normalized != "fail" if ok is None else bool(ok),
        "title": title,
        "message": message,
        "suggestion": suggestion,
        "detail": message,
        **extra,
    }


def _probe_writable_dir(path: Path) -> tuple[bool, str | None]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".__health_probe__"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _check_backend_service() -> dict[str, Any]:
    return _check(
        "backend_service",
        "pass",
        "后端服务",
        "后端 API 正在响应系统状态请求。",
        "无需处理；如果前端无法连接，请检查后端端口和桌面启动日志。",
    )


def _check_writable_dir(key: str, title: str, path: Path, suggestion: str) -> dict[str, Any]:
    writable, error = _probe_writable_dir(path)
    if not writable:
        return _check(
            key,
            "fail",
            title,
            f"{path} 不可写：{error}",
            suggestion,
            path=str(path),
            writable=False,
        )
    return _check(
        key,
        "pass",
        title,
        f"{path} 可写。",
        "无需处理。",
        path=str(path),
        writable=True,
    )


def _check_disk() -> dict[str, Any]:
    usage = shutil.disk_usage(settings.APP_HOME)
    total_gb = round(usage.total / (1024**3), 2)
    free_gb = round(usage.free / (1024**3), 2)
    used_gb = round(usage.used / (1024**3), 2)
    used_percent = round((usage.used / usage.total) * 100, 2) if usage.total else 0.0
    ok = free_gb >= float(settings.MIN_FREE_DISK_GB)
    return _check(
        "disk",
        "pass" if ok else "fail",
        "磁盘剩余空间",
        f"可用 {free_gb} GB / 总计 {total_gb} GB。",
        "空间不足时，先清理旧 outputs、调试图和临时样例，再继续分析大视频。"
        if not ok
        else "无需处理；建议长期保留至少 2 GB 可用空间。",
        path=str(settings.APP_HOME),
        total_gb=total_gb,
        used_gb=used_gb,
        free_gb=free_gb,
        used_percent=used_percent,
        min_free_gb=settings.MIN_FREE_DISK_GB,
    )


def _check_model_file() -> dict[str, Any]:
    runtime_model = settings.MODELS_DIR / "pose_landmarker_full.task"
    legacy_model = settings.LEGACY_MODELS_DIR / "pose_landmarker_full.task"
    path = runtime_model if runtime_model.exists() else legacy_model
    exists = path.exists()
    size_bytes = path.stat().st_size if exists else 0
    return _check(
        "model_file",
        "pass" if exists else "fail",
        "MediaPipe 模型文件",
        f"模型文件已就绪（{round(size_bytes / (1024**2), 2)} MB）。" if exists else "未找到 pose_landmarker_full.task。",
        "无需处理。" if exists else "请把 pose_landmarker_full.task 放到 models 目录，或重新执行项目的模型准备步骤。",
        path=str(path),
        runtime_path=str(runtime_model),
        legacy_path=str(legacy_model),
        size_bytes=size_bytes,
    )


def _check_ffmpeg() -> dict[str, Any]:
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if not ffmpeg_path or not ffprobe_path:
        missing = ", ".join(name for name, path in {"ffmpeg": ffmpeg_path, "ffprobe": ffprobe_path}.items() if not path)
        return _check(
            "ffmpeg",
            "fail",
            "ffmpeg / ffprobe",
            f"缺少 {missing}，视频转码或元信息读取会失败。",
            "请安装 ffmpeg，并确认 ffmpeg、ffprobe 已加入系统 PATH；安装后重启桌面程序。",
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
        )
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False, timeout=5)
        first_line = (result.stdout or result.stderr or "").splitlines()[0] if (result.stdout or result.stderr) else "ffmpeg available"
    except Exception as exc:
        return _check(
            "ffmpeg",
            "fail",
            "ffmpeg / ffprobe",
            f"ffmpeg 可执行文件存在，但运行失败：{type(exc).__name__}: {exc}",
            "请重新安装 ffmpeg，或检查 PATH 指向的 ffmpeg 是否可执行。",
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
        )
    return _check(
        "ffmpeg",
        "pass",
        "ffmpeg / ffprobe",
        first_line,
        "无需处理。",
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )


def _check_postgresql() -> dict[str, Any]:
    enabled = bool(settings.DATABASE_URL)
    if not enabled:
        return _check(
            "postgresql",
            "optional",
            "PostgreSQL",
            "未配置 PostgreSQL，当前会使用文件/本地存储兜底。",
            "毕业设计本地演示可以不配置；如果要长期保存大量记录，再配置 DANCE_ASSIST_DATABASE_URL。",
            enabled=False,
            required=False,
            backend=task_store.backend_name,
        )

    try:
        import psycopg  # type: ignore

        with psycopg.connect(settings.DATABASE_URL, connect_timeout=1) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user")
                row = cur.fetchone()
        return _check(
            "postgresql",
            "pass",
            "PostgreSQL",
            f"已连接到 {row[0]}，用户 {row[1]}。" if row else "数据库连接正常。",
            "无需处理。",
            enabled=True,
            required=False,
            backend=task_store.backend_name,
            database=row[0] if row else None,
            user=row[1] if row else None,
        )
    except Exception as exc:
        return _check(
            "postgresql",
            "warn",
            "PostgreSQL",
            f"已配置 PostgreSQL，但连接失败：{type(exc).__name__}: {exc}",
            "如果需要数据库持久化，请先启动 PostgreSQL 并检查连接串；若只是本地演示，可暂时使用文件兜底。",
            enabled=True,
            required=False,
            backend=task_store.backend_name,
        )


def _parse_heartbeat(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_number(value: Any) -> float | int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _compact_latest_pipeline(task: dict[str, Any]) -> dict[str, Any]:
    report = task.get("report") if isinstance(task.get("report"), dict) else {}
    scores = report.get("scores") if isinstance(report.get("scores"), dict) else {}
    confidence = report.get("confidence") if isinstance(report.get("confidence"), dict) else {}

    compact = {
        "pipeline_id": task.get("pipeline_id"),
        "status": task.get("status"),
        "progress": _safe_number(task.get("progress")),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "updated_at": task.get("updated_at"),
        "finished_at": task.get("finished_at"),
        "error_type": task.get("error_type"),
        "error_message": task.get("error_message"),
        "score_total": _safe_number(task.get("score_total") or report.get("score_0_100") or scores.get("score_total")),
        "confidence_score": _safe_number(task.get("confidence_score") or confidence.get("score")),
    }
    return {key: value for key, value in compact.items() if value is not None}


def _check_redis() -> dict[str, Any]:
    enabled = bool(settings.REDIS_URL)
    required = settings.PIPELINE_EXECUTOR == "redis_queue"
    if not enabled:
        status = "fail" if required else "optional"
        return _check(
            "redis",
            status,
            "Redis 队列",
            "当前执行器需要 Redis，但未配置 REDIS_URL。" if required else "未配置 Redis，当前不使用队列执行。",
            "请配置 DANCE_ASSIST_REDIS_URL 并启动 Redis Worker。"
            if required
            else "本地线程执行模式可以不配置；需要后台队列时再启用 Redis。",
            enabled=False,
            required=required,
            queue=settings.REDIS_PIPELINE_QUEUE,
            dead_letter_queue=settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE,
        )

    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = bool(client.ping())
        pending_jobs = int(client.llen(settings.REDIS_PIPELINE_QUEUE))
        dead_letter_jobs = int(client.llen(settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE))
        heartbeat = _parse_heartbeat(client.get(settings.REDIS_WORKER_HEARTBEAT_KEY))
        heartbeat_updated_at = heartbeat.get("updated_at")
        heartbeat_age_sec: float | None = None
        worker_alive: bool | None = None
        if isinstance(heartbeat_updated_at, str) and heartbeat_updated_at:
            try:
                heartbeat_dt = datetime.fromisoformat(heartbeat_updated_at.replace("Z", "+00:00"))
                heartbeat_age_sec = max(0.0, (datetime.now(timezone.utc) - heartbeat_dt.astimezone(timezone.utc)).total_seconds())
                worker_alive = heartbeat_age_sec <= max(10, int(settings.REDIS_WORKER_HEARTBEAT_TTL_SEC) * 1.5)
            except Exception:
                worker_alive = False if required else None
        elif required:
            worker_alive = False

        ok = pong and (not required or bool(worker_alive))
        status = "pass" if ok else ("fail" if required else "warn")
        detail_parts = []
        if pending_jobs > 0:
            detail_parts.append(f"待处理 {pending_jobs} 条")
        if dead_letter_jobs > 0:
            detail_parts.append(f"死信 {dead_letter_jobs} 条")
        if heartbeat_age_sec is not None:
            detail_parts.append(f"Worker 心跳 {heartbeat_age_sec:.1f}s 前")
        elif required:
            detail_parts.append("Worker 心跳缺失")
        message = "，".join(detail_parts) if detail_parts else "Redis 连接正常，队列空闲。"

        return _check(
            "redis",
            status,
            "Redis 队列",
            message,
            "无需处理。"
            if ok
            else ("请启动 Redis Worker，并检查死信队列中的失败任务。" if required else "Redis 是可选项；如需队列执行，请检查 Redis 服务和连接串。"),
            enabled=True,
            required=required,
            queue=settings.REDIS_PIPELINE_QUEUE,
            dead_letter_queue=settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE,
            pending_jobs=pending_jobs,
            dead_letter_jobs=dead_letter_jobs,
            worker_heartbeat_key=settings.REDIS_WORKER_HEARTBEAT_KEY,
            worker_alive=worker_alive,
            worker_state=heartbeat.get("state"),
            worker_pipeline_id=heartbeat.get("pipeline_id"),
            worker_updated_at=heartbeat_updated_at,
            worker_age_sec=round(heartbeat_age_sec, 3) if heartbeat_age_sec is not None else None,
            url=settings.REDIS_URL,
        )
    except Exception as exc:
        return _check(
            "redis",
            "fail" if required else "warn",
            "Redis 队列",
            f"Redis 连接失败：{type(exc).__name__}: {exc}",
            "如果当前使用 redis_queue，请先启动 Redis 和 Worker；如果只是本地演示，可切回 local_thread。",
            enabled=True,
            required=required,
            queue=settings.REDIS_PIPELINE_QUEUE,
            dead_letter_queue=settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE,
            url=settings.REDIS_URL,
        )


def _check_ai_provider() -> dict[str, Any]:
    provider = ai_provider_status()
    configured = bool(provider.get("configured"))
    if configured:
        return _check(
            "ai_provider",
            "pass",
            "AI provider",
            f"{provider.get('provider')} 已配置，模型：{provider.get('model') or 'local'}。",
            "无需处理。",
            **provider,
        )
    return _check(
        "ai_provider",
        "optional",
        "AI provider",
        f"{provider.get('provider')} 未配置 API Key，AI 助教会使用本地 fallback。",
        "如需云端 AI 解读，请配置对应 API Key；不配置也不会影响核心评分和报告生成。",
        **provider,
    )


def _check_recent_pipeline_failure() -> dict[str, Any]:
    tasks_dir = settings.APP_HOME / "tasks"
    try:
        candidates: list[dict[str, Any]] = []
        if tasks_dir.exists():
            for path in tasks_dir.glob("*.json"):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(payload, dict):
                    candidates.append(payload)
        candidates.sort(
            key=lambda item: str(
                item.get("updated_at")
                or item.get("finished_at")
                or item.get("started_at")
                or item.get("queued_at")
                or ""
            ),
            reverse=True,
        )
        items = candidates[:1]
    except Exception as exc:
        return _check(
            "recent_pipeline",
            "warn",
            "最近一次 pipeline",
            f"无法读取最近任务状态：{type(exc).__name__}: {exc}",
            "可以先打开分析记录确认最近任务是否正常。",
        )

    if not items:
        return _check(
            "recent_pipeline",
            "optional",
            "最近一次 pipeline",
            "暂无分析任务记录。",
            "上传教师和学员视频并完成一次分析后，这里会显示最近任务状态。",
        )

    latest = items[0]
    status = str(latest.get("status") or "").strip()
    pipeline_id = str(latest.get("pipeline_id") or "")
    if status == "failed":
        error_type = latest.get("error_type") or "unknown"
        error_message = latest.get("error_message") or f"最近任务失败：{error_type}"
        error_suggestion = latest.get("error_suggestion") or "建议打开分析记录查看失败详情，并优先检查视频是否可读、模型文件和 ffmpeg 是否正常。"
        return _check(
            "recent_pipeline",
            "warn",
            "最近一次 pipeline",
            f"{error_message}（{pipeline_id} / {error_type}）。",
            str(error_suggestion),
            latest=_compact_latest_pipeline(latest),
        )
    return _check(
        "recent_pipeline",
        "pass",
        "最近一次 pipeline",
        f"最近任务状态：{status or 'unknown'}。",
        "无需处理；如果任务长时间停在运行中，再检查 Redis/Worker 或后端日志。",
        latest=_compact_latest_pipeline(latest),
    )


def collect_health_report() -> dict[str, Any]:
    checks = {
        "backend_service": _check_backend_service(),
        "runtime_writable": _check_writable_dir(
            "runtime_writable",
            "运行目录",
            settings.APP_HOME,
            "请确认运行目录可写；桌面端需要在这里保存缓存、上传和状态文件。",
        ),
        "outputs_writable": _check_writable_dir(
            "outputs_writable",
            "outputs 目录",
            settings.OUTPUTS_DIR,
            "请确认 outputs 目录可写；分析报告、时间轴和问题索引都会写入这里。",
        ),
        "disk": _check_disk(),
        "model_file": _check_model_file(),
        "ffmpeg": _check_ffmpeg(),
        "postgresql": _check_postgresql(),
        "redis": _check_redis(),
        "ai_provider": _check_ai_provider(),
        "recent_pipeline": _check_recent_pipeline_failure(),
    }
    ok = all(check.get("status") != "fail" for check in checks.values())
    return {
        "ok": ok,
        "checked_at": _utc_now(),
        "task_store": task_store.backend_name,
        "pipeline_executor": settings.PIPELINE_EXECUTOR,
        "app_home": str(settings.APP_HOME),
        "checks": checks,
    }


def collect_basic_health() -> dict[str, Any]:
    report = collect_health_report()
    return {
        "ok": report["ok"],
        "task_store": report["task_store"],
        "pipeline_executor": report["pipeline_executor"],
    }
