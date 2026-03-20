from __future__ import annotations

import json
import shutil
import subprocess
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import HTTPException

from app.services.pipeline_executor import get_pipeline_executor_backend, submit_pipeline_job
from app.services.storage import get_video_meta
from app.services.task_store import (
    get_pipeline_failure_stats as load_pipeline_failure_stats,
    list_analysis_reports as load_analysis_report_summaries,
    list_task_summaries as load_task_summaries,
    load_analysis_report_record,
    load_task_record,
    save_pipeline_event,
    save_task_record,
)
from app.settings import settings

# Make project root importable for core/* modules.
import sys

if str(settings.PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(settings.PROJECT_ROOT))

from core.align_and_score import run_one_pair
from core.pose_mediapipe import download_if_needed, extract_pose_landmarker_video
from core.render_overlay import render_overlay_video_h264
from core.timeline import generate_timeline


_TASKS: dict[str, dict[str, Any]] = {}
_TASK_LOCK = threading.Lock()
TASKS_DIR = settings.APP_HOME / "tasks"


def _task_json_path(pipeline_id: str) -> Path:
    return TASKS_DIR / f"{pipeline_id}.json"


def _persist_task(task: dict[str, Any]) -> None:
    save_task_record(task)
    try:
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        p = _task_json_path(str(task.get("pipeline_id", "")))
        if p.name == ".json":
            return
        p.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # persistence is best-effort; in-memory flow remains primary
        pass


def _load_task_from_disk(pipeline_id: str) -> dict[str, Any] | None:
    p = _task_json_path(pipeline_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_task_from_storage(pipeline_id: str) -> dict[str, Any] | None:
    task = load_task_record(pipeline_id)
    if task:
        return task
    return _load_task_from_disk(pipeline_id)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_attempt_count(attempt_count: int | None) -> int:
    try:
        return max(1, int(attempt_count or 1))
    except Exception:
        return 1


def _classify_pipeline_error(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        if exc.status_code in {400, 404, 413}:
            return "input_error"
        return "request_error"
    if isinstance(exc, FileNotFoundError):
        return "missing_file"
    if isinstance(exc, subprocess.SubprocessError):
        return "process_error"
    if isinstance(exc, TimeoutError):
        return "timeout"
    return "internal_error"


def _record_pipeline_event(
    pipeline_id: str,
    event_type: str,
    *,
    status: str | None = None,
    message: str | None = None,
    executor: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    save_pipeline_event(
        pipeline_id,
        event_type,
        status=status,
        message=message,
        executor=executor,
        payload=payload,
    )


def _set_task(pipeline_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    with _TASK_LOCK:
        old = _TASKS.get(pipeline_id)
        if old is None:
            old = _load_task_from_storage(pipeline_id) or {}
        new = {
            **old,
            **patch,
            "pipeline_id": pipeline_id,
            "updated_at": _utc_now(),
        }
        _TASKS[pipeline_id] = new
    _persist_task(new)
    return new


def _get_task(pipeline_id: str) -> dict[str, Any]:
    # In redis_queue mode the API process and worker process do not share memory.
    # Always prefer persisted state so status/result endpoints do not get stuck on
    # stale in-memory "pending" snapshots after the worker completes.
    task = _load_task_from_storage(pipeline_id)
    if task:
        with _TASK_LOCK:
            _TASKS[pipeline_id] = task
        return task

    with _TASK_LOCK:
        task = _TASKS.get(pipeline_id)
    if task:
        return task

    raise HTTPException(status_code=404, detail=f"pipeline not found: {pipeline_id}")


def _task_pair_name(task: dict[str, Any]) -> str:
    pair_name = task.get("pair_name")
    if isinstance(pair_name, str) and pair_name.strip():
        return pair_name

    report = task.get("report")
    if isinstance(report, dict):
        report_pair_name = report.get("pair_name")
        if isinstance(report_pair_name, str) and report_pair_name.strip():
            return report_pair_name

    files = task.get("files")
    if isinstance(files, dict):
        for key in ("report_url", "timeline_json_url", "timeline_npz_url"):
            value = files.get(key)
            if not isinstance(value, str):
                continue
            parts = value.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "artifacts" and parts[1]:
                return parts[1]

    return f"pipeline_{task.get('pipeline_id', 'unknown')}"


def _task_status(task: dict[str, Any]) -> str:
    status = task.get("status")
    if isinstance(status, str) and status in {"pending", "running", "done", "failed"}:
        return status
    return "pending"


def _task_stage(task: dict[str, Any]) -> str:
    stage = task.get("stage")
    if isinstance(stage, str) and stage.strip():
        return stage
    status = _task_status(task)
    fallback = {
        "pending": "queued",
        "running": "processing",
        "done": "completed",
        "failed": "failed",
    }
    return fallback.get(status, "queued")


def _task_score_total(task: dict[str, Any]) -> float | None:
    report = task.get("report")
    if isinstance(report, dict):
        raw = report.get("score_0_100")
        if raw is None:
            scores = report.get("scores")
            if isinstance(scores, dict):
                raw = scores.get("score_total")
        try:
            value = float(raw)
        except Exception:
            return None
        return value if np.isfinite(value) else None
    return None


def _task_confidence_score(task: dict[str, Any]) -> float | None:
    report = task.get("report")
    if isinstance(report, dict):
        confidence = report.get("confidence")
        if isinstance(confidence, dict):
            try:
                value = float(confidence.get("score"))
            except Exception:
                return None
            return value if np.isfinite(value) else None
    return None


def _task_summary(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": str(task.get("pipeline_id", "") or ""),
        "pair_name": _task_pair_name(task),
        "status": _task_status(task),
        "stage": _task_stage(task),
        "progress": _task_progress(task),
        "teacher_video_id": task.get("teacher_video_id"),
        "user_video_id": task.get("user_video_id"),
        "executor": task.get("executor"),
        "attempt_count": task.get("attempt_count"),
        "retry_count": task.get("retry_count"),
        "error_type": task.get("error_type"),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "updated_at": task.get("updated_at"),
        "score_total": _task_score_total(task),
        "confidence_score": _task_confidence_score(task),
    }


def _task_progress(task: dict[str, Any]) -> float:
    try:
        progress = float(task.get("progress"))
    except Exception:
        progress = 0.0
    if not np.isfinite(progress):
        progress = 0.0
    return float(np.clip(progress, 0.0, 1.0))


def _update_task_progress(
    pipeline_id: str,
    *,
    stage: str,
    message: str,
    progress: float,
    status: str = "running",
    **extra: Any,
) -> dict[str, Any]:
    patch = {
        "status": status,
        "stage": stage,
        "message": message,
        "progress": float(np.clip(progress, 0.0, 1.0)),
    }
    patch.update(extra)
    return _set_task(pipeline_id, patch)


def _ffmpeg_convert_to_mp4(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-r",
        "30",
        "-vf",
        "scale=-2:720",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg convert failed: {r.stderr}")


def _prepare_video(src: Path, dst_mp4: Path, overwrite: bool) -> Path:
    dst_mp4.parent.mkdir(parents=True, exist_ok=True)
    if dst_mp4.exists() and (not overwrite):
        return dst_mp4

    # Always normalize to CFR mp4 for stable downstream pose/timeline/overlay sync.
    _ffmpeg_convert_to_mp4(src, dst_mp4)
    return dst_mp4


def _ensure_pose_cache(
    tag: str,
    stem: str,
    video_path: Path,
    model_path: Path,
    cache_dir: Path,
    overwrite: bool,
) -> tuple[Path, Path, Path]:
    out_norm = cache_dir / f"{tag}__{stem}__norm.npy"
    out_world = cache_dir / f"{tag}__{stem}__world.npy"
    out_meta = cache_dir / f"{tag}__{stem}__meta.json"

    if (not overwrite) and out_norm.exists() and out_world.exists() and out_meta.exists():
        return out_norm, out_world, out_meta

    extract_pose_landmarker_video(
        video_path=video_path,
        model_path=model_path,
        out_norm_npy=out_norm,
        out_world_npy=out_world,
        out_meta_json=out_meta,
        out_overlay_video=None,
        max_frames=0,
    )
    return out_norm, out_world, out_meta


def _artifact_url(pair_name: str, filename: str) -> str:
    return f"/artifacts/{pair_name}/{filename}"


def _seed_model_from_legacy(models_dir: Path) -> None:
    legacy_model = settings.LEGACY_MODELS_DIR / "pose_landmarker_full.task"
    target_model = models_dir / "pose_landmarker_full.task"
    if target_model.exists() or (not legacy_model.exists()):
        return
    target_model.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy_model, target_model)


def _cleanup_old_output_pairs(exclude_pair: str | None = None) -> None:
    keep = int(getattr(settings, "RETAIN_OUTPUT_PAIRS", 0))
    if keep <= 0:
        return

    root = settings.OUTPUTS_DIR
    if not root.exists():
        return

    pairs = [p for p in root.iterdir() if p.is_dir()]
    pairs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    kept = 0
    for p in pairs:
        if exclude_pair and p.name == exclude_pair:
            continue
        if kept < keep:
            kept += 1
            continue
        shutil.rmtree(p, ignore_errors=True)


def _pipeline_worker(
    pipeline_id: str,
    teacher_video_id: str,
    user_video_id: str,
    overwrite: bool,
    *,
    raise_on_error: bool = False,
    attempt_count: int | None = None,
    executor_backend: str | None = None,
) -> bool:
    current_attempt = _normalize_attempt_count(attempt_count)
    resolved_executor = executor_backend or get_pipeline_executor_backend()

    try:
        _update_task_progress(
            pipeline_id,
            stage="preparing_inputs",
            message="preparing source videos",
            progress=0.08,
            status="running",
            started_at=_utc_now(),
            finished_at=None,
            executor=resolved_executor,
            attempt_count=current_attempt,
            retry_count=max(0, current_attempt - 1),
            error_type=None,
        )
        _record_pipeline_event(
            pipeline_id,
            "started",
            status="running",
            message="pipeline started",
            executor=resolved_executor,
            payload={"attempt_count": current_attempt},
        )

        teacher_meta = get_video_meta(teacher_video_id, role="teacher")
        user_meta = get_video_meta(user_video_id, role="user")

        teacher_stem = f"teacher_{teacher_video_id}"
        user_stem = f"user_{user_video_id}"
        pair_name = f"{teacher_stem}_vs_{user_stem}"

        standard_dir = settings.DATA_DIR / "standard_videos"
        user_dir = settings.DATA_DIR / "user_videos"
        cache_dir = settings.DATA_DIR / "cache_keypoints"
        models_dir = settings.MODELS_DIR
        outputs_dir = settings.OUTPUTS_DIR

        for p in [standard_dir, user_dir, cache_dir, models_dir, outputs_dir]:
            p.mkdir(parents=True, exist_ok=True)

        t_src = Path(teacher_meta["path"])
        u_src = Path(user_meta["path"])

        t_video = _prepare_video(t_src, standard_dir / f"{teacher_stem}.mp4", overwrite=overwrite)
        u_video = _prepare_video(u_src, user_dir / f"{user_stem}.mp4", overwrite=overwrite)

        _update_task_progress(
            pipeline_id,
            stage="extracting_pose",
            message="extracting pose landmarks",
            progress=0.28,
            pair_name=pair_name,
        )

        _seed_model_from_legacy(models_dir)
        model_path = download_if_needed(models_dir / "pose_landmarker_full.task", prefer_full=True)

        t_norm, _, _ = _ensure_pose_cache(
            tag="standard",
            stem=teacher_stem,
            video_path=t_video,
            model_path=model_path,
            cache_dir=cache_dir,
            overwrite=overwrite,
        )
        u_norm, _, _ = _ensure_pose_cache(
            tag="user",
            stem=user_stem,
            video_path=u_video,
            model_path=model_path,
            cache_dir=cache_dir,
            overwrite=overwrite,
        )

        _update_task_progress(
            pipeline_id,
            stage="aligning_motion",
            message="aligning motion and scoring",
            progress=0.62,
            pair_name=pair_name,
        )

        run_root = settings.APP_HOME
        run_one_pair(run_root, teacher_stem, user_stem)
        generate_timeline(run_root, teacher_stem, user_stem, marker_topk=10)

        pair_dir = settings.OUTPUTS_DIR / pair_name
        t_overlay = pair_dir / f"{teacher_stem}_overlay_h264.mp4"
        u_overlay = pair_dir / f"{user_stem}_overlay_h264.mp4"

        _update_task_progress(
            pipeline_id,
            stage="rendering_outputs",
            message="rendering comparison outputs",
            progress=0.82,
            pair_name=pair_name,
        )

        render_overlay_video_h264(t_video, t_norm, t_overlay, overwrite=overwrite)
        render_overlay_video_h264(u_video, u_norm, u_overlay, overwrite=overwrite)

        report_path = pair_dir / "report.json"
        timeline_json = pair_dir / "timeline.json"
        timeline_npz = pair_dir / "timeline.npz"

        _update_task_progress(
            pipeline_id,
            stage="packaging_results",
            message="loading analysis artifacts",
            progress=0.94,
            pair_name=pair_name,
        )

        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        timeline = json.loads(timeline_json.read_text(encoding="utf-8")) if timeline_json.exists() else None
        if timeline is None:
            timeline = {}
        if timeline_npz.exists():
            tl = np.load(timeline_npz)
            timeline["fps_teacher"] = float(tl["fps_teacher"]) if "fps_teacher" in tl.files else timeline.get("fps_teacher")
            timeline["fps_user"] = float(tl["fps_user"]) if "fps_user" in tl.files else timeline.get("fps_user")
            timeline["teacher_frames"] = int(tl["teacher_frames"]) if "teacher_frames" in tl.files else timeline.get("teacher_frames")
            timeline["user_frames"] = int(tl["user_frames"]) if "user_frames" in tl.files else timeline.get("user_frames")
            if "map_user_sec" in tl.files:
                timeline["map_user_sec"] = tl["map_user_sec"].astype(np.float32).tolist()
            if "teacher_to_user" in tl.files:
                timeline["teacher_to_user"] = tl["teacher_to_user"].astype(np.int32).tolist()
            if "frame_quality" in tl.files:
                timeline["frame_quality"] = tl["frame_quality"].astype(np.float32).tolist()
            if "marker_frames" in tl.files:
                timeline["marker_frames"] = tl["marker_frames"].astype(np.int32).tolist()
            if "marker_types" in tl.files:
                timeline["marker_types"] = tl["marker_types"].astype(np.int8).tolist()

        files = {
            "report_url": _artifact_url(pair_name, "report.json"),
            "summary_url": _artifact_url(pair_name, "summary.json"),
            "timeline_npz_url": _artifact_url(pair_name, "timeline.npz"),
            "timeline_json_url": _artifact_url(pair_name, "timeline.json"),
            "teacher_overlay_url": _artifact_url(pair_name, t_overlay.name),
            "user_overlay_url": _artifact_url(pair_name, u_overlay.name),
            "error_curve_url": _artifact_url(pair_name, "error_curve.png"),
            "tempo_curve_url": _artifact_url(pair_name, "tempo_curve.png"),
            "top_joints_url": _artifact_url(pair_name, "top_joints.png"),
            "keyframes_compare_url": _artifact_url(pair_name, "keyframes_compare.png"),
        }

        _update_task_progress(
            pipeline_id,
            stage="completed",
            message="pipeline completed",
            progress=1.0,
            status="done",
            finished_at=_utc_now(),
            pair_name=pair_name,
            attempt_count=current_attempt,
            retry_count=max(0, current_attempt - 1),
            report=report,
            timeline=timeline,
            files=files,
            error_type=None,
        )
        _record_pipeline_event(
            pipeline_id,
            "completed",
            status="done",
            message="pipeline completed",
            executor=resolved_executor,
            payload={"pair_name": pair_name, "attempt_count": current_attempt},
        )

        _cleanup_old_output_pairs(exclude_pair=pair_name)
        return True
    except Exception as exc:
        error_type = _classify_pipeline_error(exc)
        _update_task_progress(
            pipeline_id,
            stage="failed",
            message=f"{type(exc).__name__}: {exc}",
            progress=1.0,
            status="failed",
            error=traceback.format_exc(),
            error_type=error_type,
            finished_at=_utc_now(),
            attempt_count=current_attempt,
            retry_count=max(0, current_attempt - 1),
        )
        _record_pipeline_event(
            pipeline_id,
            "failed",
            status="failed",
            message=f"{type(exc).__name__}: {exc}",
            executor=resolved_executor,
            payload={"error_type": error_type, "attempt_count": current_attempt},
        )
        if raise_on_error:
            raise
        return False


def run_pipeline(teacher_video_id: str, user_video_id: str, overwrite: bool = False) -> dict[str, Any]:
    teacher_meta = get_video_meta(teacher_video_id, role="teacher")
    user_meta = get_video_meta(user_video_id, role="user")

    pipeline_id = uuid.uuid4().hex[:16]
    pair_name = f"teacher_{teacher_meta['video_id']}_vs_user_{user_meta['video_id']}"

    executor_backend = get_pipeline_executor_backend()
    _set_task(
        pipeline_id,
        {
            "pair_name": pair_name,
            "status": "pending",
            "stage": "queued",
            "progress": 0.0,
            "message": "queued",
            "teacher_video_id": teacher_video_id,
            "user_video_id": user_video_id,
            "queued_at": _utc_now(),
            "started_at": None,
            "finished_at": None,
            "executor": executor_backend,
            "attempt_count": 1,
            "retry_count": 0,
            "error_type": None,
            "report": None,
            "timeline": None,
            "files": None,
        },
    )
    _record_pipeline_event(
        pipeline_id,
        "queued",
        status="pending",
        message="pipeline queued",
        executor=executor_backend,
        payload={
            "teacher_video_id": teacher_video_id,
            "user_video_id": user_video_id,
            "overwrite": overwrite,
            "attempt_count": 1,
        },
    )

    try:
        submit_pipeline_job(
            worker=_pipeline_worker,
            pipeline_id=pipeline_id,
            teacher_video_id=teacher_video_id,
            user_video_id=user_video_id,
            overwrite=overwrite,
        )
    except Exception as exc:
        error_type = _classify_pipeline_error(exc)
        _update_task_progress(
            pipeline_id,
            stage="failed",
            message=f"{type(exc).__name__}: {exc}",
            progress=1.0,
            status="failed",
            finished_at=_utc_now(),
            error_type=error_type,
        )
        _record_pipeline_event(
            pipeline_id,
            "submit_failed",
            status="failed",
            message=f"{type(exc).__name__}: {exc}",
            executor=executor_backend,
            payload={"error_type": error_type, "attempt_count": 1},
        )
        raise
    return _get_task(pipeline_id)


def list_pipeline_tasks(limit: int = 50, status: str | None = None) -> dict[str, Any]:
    safe_limit = max(1, min(200, int(limit)))
    normalized_status = status or None
    if normalized_status == "all":
        normalized_status = None

    items = load_task_summaries(limit=safe_limit, status=normalized_status)
    if not items:
        task_ids: set[str] = set()
        with _TASK_LOCK:
            task_ids.update(_TASKS.keys())
        if TASKS_DIR.exists():
            task_ids.update(path.stem for path in TASKS_DIR.glob("*.json"))

        fallback_items: list[dict[str, Any]] = []
        for pipeline_id in task_ids:
            task = _load_task_from_storage(pipeline_id)
            if not task:
                continue
            summary = _task_summary(task)
            if normalized_status and summary["status"] != normalized_status:
                continue
            fallback_items.append(summary)

        items = sorted(
            fallback_items,
            key=lambda item: item.get("updated_at") or item.get("finished_at") or item.get("started_at") or item.get("queued_at") or "",
            reverse=True,
        )[:safe_limit]

    return {
        "items": items,
        "total": len(items),
        "status_filter": normalized_status,
        "limit": safe_limit,
    }


def list_analysis_reports(
    limit: int = 50,
    query: str | None = None,
    min_score: float | None = None,
    min_confidence: float | None = None,
) -> dict[str, Any]:
    safe_limit = max(1, min(200, int(limit)))
    items = load_analysis_report_summaries(
        limit=safe_limit,
        query=query,
        min_score=min_score,
        min_confidence=min_confidence,
    )

    if not items:
        fallback_items: list[dict[str, Any]] = []
        for item in list_pipeline_tasks(limit=safe_limit, status="done").get("items", []):
            detail = load_analysis_report_record(item.get("pipeline_id", ""))
            if detail:
                fallback_items.append(detail)
                continue
            try:
                task = _get_task(item.get("pipeline_id", ""))
            except HTTPException:
                continue
            report = task.get("report") if isinstance(task.get("report"), dict) else {}
            confidence = report.get("confidence") if isinstance(report, dict) else {}
            recommendations = report.get("recommendations") if isinstance(report, dict) else {}
            beginner_report = report.get("beginner_report") if isinstance(report, dict) else {}
            teaching_report = report.get("teaching_report") if isinstance(report, dict) else {}
            scores = report.get("scores") if isinstance(report, dict) else {}
            fallback_items.append(
                {
                    **item,
                    "score_pose": scores.get("score_pose") if isinstance(scores, dict) else None,
                    "score_tempo": scores.get("score_tempo") if isinstance(scores, dict) else None,
                    "confidence_level": confidence.get("level") if isinstance(confidence, dict) else None,
                    "overall_advice": recommendations.get("overall") if isinstance(recommendations, dict) else None,
                    "confidence_summary": confidence.get("summary") if isinstance(confidence, dict) else None,
                    "beginner_summary": beginner_report.get("summary") if isinstance(beginner_report, dict) else None,
                    "teaching_summary": teaching_report.get("summary") if isinstance(teaching_report, dict) else None,
                    "top_joints": report.get("top_joints") if isinstance(report.get("top_joints"), list) else [],
                    "files": task.get("files") if isinstance(task.get("files"), dict) else {},
                }
            )
        items = fallback_items

    return {
        "items": items,
        "total": len(items),
        "limit": safe_limit,
        "query": query or None,
        "min_score": min_score,
        "min_confidence": min_confidence,
    }


def get_analysis_report(pipeline_id: str) -> dict[str, Any]:
    detail = load_analysis_report_record(pipeline_id)
    if detail:
        return detail

    summary = get_pipeline_result_summary(pipeline_id)
    report = summary.get("report") if isinstance(summary.get("report"), dict) else {}
    confidence = report.get("confidence") if isinstance(report, dict) else {}
    recommendations = report.get("recommendations") if isinstance(report, dict) else {}
    beginner_report = report.get("beginner_report") if isinstance(report, dict) else {}
    teaching_report = report.get("teaching_report") if isinstance(report, dict) else {}
    scores = report.get("scores") if isinstance(report, dict) else {}
    return {
        **summary,
        "teacher_video_id": None,
        "user_video_id": None,
        "score_total": _task_score_total({"report": report}),
        "score_pose": scores.get("score_pose") if isinstance(scores, dict) else None,
        "score_tempo": scores.get("score_tempo") if isinstance(scores, dict) else None,
        "confidence_score": _task_confidence_score({"report": report}),
        "confidence_level": confidence.get("level") if isinstance(confidence, dict) else None,
        "overall_advice": recommendations.get("overall") if isinstance(recommendations, dict) else None,
        "confidence_summary": confidence.get("summary") if isinstance(confidence, dict) else None,
        "beginner_summary": beginner_report.get("summary") if isinstance(beginner_report, dict) else None,
        "teaching_summary": teaching_report.get("summary") if isinstance(teaching_report, dict) else None,
        "top_joints": report.get("top_joints") if isinstance(report.get("top_joints"), list) else [],
    }


def get_pipeline_status(pipeline_id: str) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": _task_pair_name(task),
        "status": _task_status(task),
        "message": task.get("message"),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "updated_at": task.get("updated_at"),
        "executor": task.get("executor"),
        "attempt_count": task.get("attempt_count"),
        "retry_count": task.get("retry_count"),
        "error_type": task.get("error_type"),
        "stage": _task_stage(task),
        "progress": _task_progress(task),
    }


def _summarize_report(report: dict | None) -> dict | None:
    if not isinstance(report, dict):
        return report

    out = {k: v for k, v in report.items() if k != "frame_analysis"}
    rows = report.get("frame_analysis")
    if isinstance(rows, list):
        out["frame_analysis_count"] = len(rows)
    return out


def _summarize_timeline(timeline: dict | None) -> dict | None:
    if not isinstance(timeline, dict):
        return timeline

    out: dict[str, Any] = {}
    heavy_arrays = {"map_user_sec", "teacher_to_user", "frame_quality"}
    marker_arrays = {"marker_frames", "marker_types"}

    for k, v in timeline.items():
        if k in heavy_arrays and isinstance(v, list):
            out[f"{k}_count"] = len(v)
            if v:
                out[f"{k}_preview"] = [v[0], v[min(len(v) - 1, len(v) // 2)], v[-1]]
            continue

        if k in marker_arrays and isinstance(v, list):
            out[f"{k}_count"] = len(v)
            out[k] = v[:200]
            continue

        out[k] = v

    return out


def get_pipeline_result(pipeline_id: str) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": _task_pair_name(task),
        "status": _task_status(task),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "updated_at": task.get("updated_at"),
        "executor": task.get("executor"),
        "attempt_count": task.get("attempt_count"),
        "retry_count": task.get("retry_count"),
        "error_type": task.get("error_type"),
        "stage": _task_stage(task),
        "progress": _task_progress(task),
        "report": task.get("report"),
        "timeline": task.get("timeline"),
        "files": task.get("files"),
    }


def get_pipeline_result_summary(pipeline_id: str) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": _task_pair_name(task),
        "status": _task_status(task),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "updated_at": task.get("updated_at"),
        "executor": task.get("executor"),
        "attempt_count": task.get("attempt_count"),
        "retry_count": task.get("retry_count"),
        "error_type": task.get("error_type"),
        "stage": _task_stage(task),
        "progress": _task_progress(task),
        "report": _summarize_report(task.get("report")),
        "timeline": _summarize_timeline(task.get("timeline")),
        "files": task.get("files"),
    }


def get_pipeline_frame_detail(pipeline_id: str, frame: int) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    report = task.get("report") or {}
    rows = report.get("frame_analysis") if isinstance(report, dict) else None

    if not isinstance(rows, list):
        return {
            "pipeline_id": task.get("pipeline_id", pipeline_id),
            "pair_name": _task_pair_name(task),
            "status": _task_status(task),
            "frame": frame,
            "frame_analysis": None,
        }

    if frame < 0 or frame >= len(rows):
        raise HTTPException(status_code=404, detail=f"frame out of range: {frame}")

    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": _task_pair_name(task),
        "status": _task_status(task),
        "frame": frame,
        "frame_analysis": rows[frame],
    }


def get_pipeline_failure_stats(days: int = 30, limit: int = 20) -> dict[str, Any]:
    return load_pipeline_failure_stats(days=days, limit=limit)
