from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import HTTPException

from app.services.error_mapping import build_failure_payload, input_quality_failure, map_pipeline_exception
from app.services.issue_index import delete_issue_index, save_issue_index
from app.services.pipeline_executor import get_pipeline_executor_backend, submit_pipeline_job
from app.services.record_flags import delete_record_flags
from app.services.storage import get_video_meta
from app.services.video_quality import check_video_pair_quality
from app.services.task_store import (
    delete_pipeline_record,
    get_pipeline_failure_stats as load_pipeline_failure_stats,
    list_analysis_reports as load_analysis_report_summaries,
    list_task_summaries as load_task_summaries,
    load_analysis_report_record,
    load_frame_analysis_range as load_frame_analysis_range_records,
    load_task_record,
    save_pipeline_event,
    save_task_record,
)
from app.services.pipeline_views import (
    analysis_report_fallback_item,
    analysis_report_payload_from_summary,
    pipeline_frame_detail_payload,
    pipeline_frame_range_payload,
    pipeline_result_payload,
    pipeline_result_summary_payload,
    pipeline_status_payload,
    resolve_frame_window,
    task_summary,
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


def _drop_task_file(pipeline_id: str) -> bool:
    path = _task_json_path(pipeline_id)
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except Exception:
        return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_attempt_count(attempt_count: int | None) -> int:
    try:
        return max(1, int(attempt_count or 1))
    except Exception:
        return 1


def _classify_pipeline_error(exc: Exception) -> str:
    return map_pipeline_exception(exc)["error_type"]


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


def _is_cancel_requested(task: dict[str, Any] | None) -> bool:
    if not isinstance(task, dict):
        return False
    if str(task.get("status", "")).strip() == "canceled":
        return True
    return bool(task.get("cancel_requested"))


def _mark_task_canceled(
    pipeline_id: str,
    *,
    executor: str | None = None,
    message: str = "pipeline canceled by user",
) -> dict[str, Any]:
    existing = _load_task_from_storage(pipeline_id) or {}
    cancel_requested_at = existing.get("cancel_requested_at") or _utc_now()
    task = _set_task(
        pipeline_id,
        {
            "status": "canceled",
            "stage": "canceled",
            "message": message,
            "finished_at": existing.get("finished_at") or _utc_now(),
            "executor": executor or existing.get("executor"),
            **build_failure_payload("canceled", raw_error=message),
            "cancel_requested": True,
            "cancel_requested_at": cancel_requested_at,
        },
    )
    if str(existing.get("status", "")).strip() != "canceled":
        _record_pipeline_event(
            pipeline_id,
            "canceled",
            status="canceled",
            message=message,
            executor=executor or str(existing.get("executor", "")).strip() or None,
            payload={**build_failure_payload("canceled", raw_error=message), "cancel_requested_at": cancel_requested_at},
        )
    return task


def _cancel_if_requested(pipeline_id: str, *, executor: str | None = None) -> bool:
    task = _load_task_from_storage(pipeline_id)
    if not _is_cancel_requested(task):
        return False
    _mark_task_canceled(pipeline_id, executor=executor)
    return True


def _normalize_timeout_sec(timeout_sec: int | None) -> int | None:
    try:
        value = int(timeout_sec or 0)
    except Exception:
        return None
    return value if value > 0 else None


def _raise_if_pipeline_timeout(
    pipeline_id: str,
    *,
    started_monotonic: float,
    timeout_sec: int | None,
    executor: str | None = None,
    stage: str | None = None,
) -> None:
    normalized_timeout = _normalize_timeout_sec(timeout_sec)
    if normalized_timeout is None:
        return
    elapsed_sec = time.monotonic() - started_monotonic
    if elapsed_sec <= normalized_timeout:
        return
    stage_label = stage or "processing"
    task = _set_task(
        pipeline_id,
        {
            "stage": stage_label,
            "message": f"pipeline timed out after {int(elapsed_sec)}s during {stage_label}",
            **build_failure_payload(
                "timeout",
                raw_error=f"pipeline timed out after {int(elapsed_sec)}s during {stage_label}",
            ),
            "timeout_sec": normalized_timeout,
            "timeout_at": _utc_now(),
        },
    )
    _record_pipeline_event(
        pipeline_id,
        "timeout_detected",
        status=str(task.get("status", "running")).strip() or "running",
        message=f"pipeline timed out after {int(elapsed_sec)}s during {stage_label}",
        executor=executor,
        payload={
            **build_failure_payload(
                "timeout",
                raw_error=f"pipeline timed out after {int(elapsed_sec)}s during {stage_label}",
            ),
            "timeout_sec": normalized_timeout,
            "elapsed_sec": round(elapsed_sec, 3),
            "stage": stage_label,
        },
    )
    raise TimeoutError(f"pipeline exceeded timeout of {normalized_timeout}s during {stage_label}")


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _attach_input_quality(pair_dir: Path, report: dict[str, Any] | None, input_quality: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(report, dict):
        return report

    report["input_quality"] = input_quality
    report_path = pair_dir / "report.json"
    _write_json(report_path, report)

    summary_path = pair_dir / "summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            summary = {}
        if isinstance(summary, dict):
            summary["input_quality_level"] = input_quality.get("level")
            summary["input_quality_summary"] = input_quality.get("summary")
            _write_json(summary_path, summary)

    return report


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
    timeout_sec: int | None = None,
) -> bool:
    current_attempt = _normalize_attempt_count(attempt_count)
    resolved_executor = executor_backend or get_pipeline_executor_backend()
    resolved_timeout_sec = _normalize_timeout_sec(timeout_sec if timeout_sec is not None else settings.PIPELINE_JOB_TIMEOUT_SEC)
    started_monotonic = time.monotonic()

    try:
        if _cancel_if_requested(pipeline_id, executor=resolved_executor):
            return False
        _raise_if_pipeline_timeout(
            pipeline_id,
            started_monotonic=started_monotonic,
            timeout_sec=resolved_timeout_sec,
            executor=resolved_executor,
            stage="preparing_inputs",
        )

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
            timeout_sec=resolved_timeout_sec,
            timeout_at=None,
        )
        _record_pipeline_event(
            pipeline_id,
            "started",
            status="running",
            message="pipeline started",
            executor=resolved_executor,
            payload={"attempt_count": current_attempt, "timeout_sec": resolved_timeout_sec},
        )

        teacher_meta = get_video_meta(teacher_video_id, role="teacher")
        user_meta = get_video_meta(user_video_id, role="user")
        input_quality = check_video_pair_quality(teacher_video_id=teacher_video_id, user_video_id=user_video_id)
        if input_quality.get("level") == "error":
            raise input_quality_failure(input_quality)

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

        if _cancel_if_requested(pipeline_id, executor=resolved_executor):
            return False
        _raise_if_pipeline_timeout(
            pipeline_id,
            started_monotonic=started_monotonic,
            timeout_sec=resolved_timeout_sec,
            executor=resolved_executor,
            stage="extracting_pose",
        )

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

        if _cancel_if_requested(pipeline_id, executor=resolved_executor):
            return False
        _raise_if_pipeline_timeout(
            pipeline_id,
            started_monotonic=started_monotonic,
            timeout_sec=resolved_timeout_sec,
            executor=resolved_executor,
            stage="aligning_motion",
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

        if _cancel_if_requested(pipeline_id, executor=resolved_executor):
            return False
        _raise_if_pipeline_timeout(
            pipeline_id,
            started_monotonic=started_monotonic,
            timeout_sec=resolved_timeout_sec,
            executor=resolved_executor,
            stage="rendering_outputs",
        )

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

        if _cancel_if_requested(pipeline_id, executor=resolved_executor):
            return False
        _raise_if_pipeline_timeout(
            pipeline_id,
            started_monotonic=started_monotonic,
            timeout_sec=resolved_timeout_sec,
            executor=resolved_executor,
            stage="packaging_results",
        )

        _update_task_progress(
            pipeline_id,
            stage="packaging_results",
            message="loading analysis artifacts",
            progress=0.94,
            pair_name=pair_name,
        )

        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        report = _attach_input_quality(pair_dir, report, input_quality)
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
            "issues_url": _artifact_url(pair_name, "issues.json"),
            "timeline_npz_url": _artifact_url(pair_name, "timeline.npz"),
            "timeline_json_url": _artifact_url(pair_name, "timeline.json"),
            "teacher_overlay_url": _artifact_url(pair_name, t_overlay.name),
            "user_overlay_url": _artifact_url(pair_name, u_overlay.name),
            "error_curve_url": _artifact_url(pair_name, "error_curve.png"),
            "tempo_curve_url": _artifact_url(pair_name, "tempo_curve.png"),
            "top_joints_url": _artifact_url(pair_name, "top_joints.png"),
            "keyframes_compare_url": _artifact_url(pair_name, "keyframes_compare.png"),
        }

        completed_task = _update_task_progress(
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
            error_message=None,
            error_suggestion=None,
            raw_error=None,
        )
        try:
            save_issue_index(analysis_report_payload_from_summary(completed_task))
        except Exception:
            pass
        _record_pipeline_event(
            pipeline_id,
            "completed",
            status="done",
            message="pipeline completed",
            executor=resolved_executor,
            payload={"pair_name": pair_name, "attempt_count": current_attempt, "timeout_sec": resolved_timeout_sec},
        )

        _cleanup_old_output_pairs(exclude_pair=pair_name)
        return True
    except Exception as exc:
        failure = map_pipeline_exception(exc)
        _update_task_progress(
            pipeline_id,
            stage="failed",
            message=failure["error_message"],
            progress=1.0,
            status="failed",
            error=traceback.format_exc(),
            **failure,
            finished_at=_utc_now(),
            attempt_count=current_attempt,
            retry_count=max(0, current_attempt - 1),
        )
        _record_pipeline_event(
            pipeline_id,
            "failed",
            status="failed",
            message=failure["error_message"],
            executor=resolved_executor,
            payload={**failure, "attempt_count": current_attempt, "timeout_sec": resolved_timeout_sec},
        )
        if raise_on_error:
            raise
        return False


def request_pipeline_cancel(pipeline_id: str) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    status = str(task.get("status", "")).strip()
    if status in {"done", "failed", "canceled"}:
        return pipeline_status_payload(task, pipeline_id)

    if _is_cancel_requested(task):
        return pipeline_status_payload(task, pipeline_id)

    cancel_requested_at = _utc_now()
    executor = str(task.get("executor", "")).strip() or None
    if status == "pending":
        task = _mark_task_canceled(
            pipeline_id,
            executor=executor,
            message="pipeline canceled before execution started",
        )
        return pipeline_status_payload(task, pipeline_id)

    task = _set_task(
        pipeline_id,
        {
            "cancel_requested": True,
            "cancel_requested_at": cancel_requested_at,
            "message": "cancel requested, waiting for current step to finish",
            "error_type": "canceled",
        },
    )
    _record_pipeline_event(
        pipeline_id,
        "cancel_requested",
        status=status or "running",
        message="cancel requested by user",
        executor=executor,
        payload={"cancel_requested_at": cancel_requested_at},
    )
    return pipeline_status_payload(task, pipeline_id)


def remove_pipeline_task(pipeline_id: str) -> dict[str, Any]:
    pipeline_id = str(pipeline_id).strip()
    if not pipeline_id:
        raise HTTPException(status_code=400, detail="pipeline id is required")

    task = _load_task_from_storage(pipeline_id)
    if task is None:
        with _TASK_LOCK:
            task = _TASKS.get(pipeline_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"pipeline not found: {pipeline_id}")

    status = str(task.get("status", "")).strip()
    if status in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="running task cannot be deleted")

    record_deleted = delete_pipeline_record(pipeline_id)
    delete_issue_index(task)
    try:
        delete_record_flags(pipeline_id)
    except Exception:
        pass
    file_deleted = _drop_task_file(pipeline_id)
    with _TASK_LOCK:
        removed = _TASKS.pop(pipeline_id, None)

    if removed is None and not record_deleted and not file_deleted:
        raise HTTPException(status_code=404, detail=f"pipeline not found: {pipeline_id}")

    return {
        "ok": True,
        "pipeline_id": pipeline_id,
        "message": "pipeline deleted",
    }


def _enqueue_pipeline_task(
    pipeline_id: str,
    *,
    pair_name: str,
    teacher_video_id: str,
    user_video_id: str,
    overwrite: bool,
    event_type: str = "queued",
    event_message: str = "pipeline queued",
    event_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    executor_backend = get_pipeline_executor_backend()
    timeout_sec = _normalize_timeout_sec(settings.PIPELINE_JOB_TIMEOUT_SEC)
    task_patch = {
        "pair_name": pair_name,
        "status": "pending",
        "stage": "queued",
        "progress": 0.0,
        "message": event_message,
        "teacher_video_id": teacher_video_id,
        "user_video_id": user_video_id,
        "queued_at": _utc_now(),
        "started_at": None,
        "finished_at": None,
        "executor": executor_backend,
        "attempt_count": 1,
        "retry_count": 0,
        "error_type": None,
        "error_message": None,
        "error_suggestion": None,
        "raw_error": None,
        "report": None,
        "timeline": None,
        "files": None,
        "cancel_requested": False,
        "cancel_requested_at": None,
        "timeout_sec": timeout_sec,
        "timeout_at": None,
    }
    _set_task(pipeline_id, task_patch)
    payload = {
        "teacher_video_id": teacher_video_id,
        "user_video_id": user_video_id,
        "overwrite": overwrite,
        "attempt_count": 1,
        "timeout_sec": timeout_sec,
    }
    if event_payload:
        payload.update(event_payload)
    _record_pipeline_event(
        pipeline_id,
        event_type,
        status="pending",
        message=event_message,
        executor=executor_backend,
        payload=payload,
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
        failure = map_pipeline_exception(exc)
        _update_task_progress(
            pipeline_id,
            stage="failed",
            message=failure["error_message"],
            progress=1.0,
            status="failed",
            finished_at=_utc_now(),
            **failure,
        )
        failure_payload = {
            **failure,
            "attempt_count": 1,
            "timeout_sec": timeout_sec,
            "source_event": event_type,
        }
        if event_payload:
            failure_payload.update(event_payload)
        _record_pipeline_event(
            pipeline_id,
            "submit_failed",
            status="failed",
            message=failure["error_message"],
            executor=executor_backend,
            payload=failure_payload,
        )
        raise
    return _get_task(pipeline_id)


def request_pipeline_retry(pipeline_id: str, overwrite: bool = False) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    status = str(task.get("status", "")).strip()
    if status in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="pipeline is still running")

    teacher_video_id = str(task.get("teacher_video_id", "")).strip()
    user_video_id = str(task.get("user_video_id", "")).strip()
    if not teacher_video_id or not user_video_id:
        raise HTTPException(status_code=400, detail="pipeline retry requires teacher/user video ids")

    teacher_meta = get_video_meta(teacher_video_id, role="teacher")
    user_meta = get_video_meta(user_video_id, role="user")
    pair_name = f"teacher_{teacher_meta['video_id']}_vs_user_{user_meta['video_id']}"
    previous_status = status or None
    previous_attempt_count = task.get("attempt_count")
    previous_retry_count = task.get("retry_count")
    previous_error_type = task.get("error_type")

    return _enqueue_pipeline_task(
        pipeline_id,
        pair_name=pair_name,
        teacher_video_id=teacher_video_id,
        user_video_id=user_video_id,
        overwrite=overwrite,
        event_type="manual_retry_queued",
        event_message="pipeline manually re-queued",
        event_payload={
            "previous_status": previous_status,
            "previous_attempt_count": previous_attempt_count,
            "previous_retry_count": previous_retry_count,
            "previous_error_type": previous_error_type,
            "retry_origin": "manual",
        },
    )


def run_pipeline(teacher_video_id: str, user_video_id: str, overwrite: bool = False) -> dict[str, Any]:
    teacher_meta = get_video_meta(teacher_video_id, role="teacher")
    user_meta = get_video_meta(user_video_id, role="user")

    pipeline_id = uuid.uuid4().hex[:16]
    pair_name = f"teacher_{teacher_meta['video_id']}_vs_user_{user_meta['video_id']}"
    return _enqueue_pipeline_task(
        pipeline_id,
        pair_name=pair_name,
        teacher_video_id=teacher_video_id,
        user_video_id=user_video_id,
        overwrite=overwrite,
    )


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
            summary = task_summary(task)
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
            fallback_items.append(analysis_report_fallback_item(item, task))
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
    return analysis_report_payload_from_summary(summary)


def get_pipeline_status(pipeline_id: str) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    return pipeline_status_payload(task, pipeline_id)


def get_pipeline_result(pipeline_id: str) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    return pipeline_result_payload(task, pipeline_id)


def get_pipeline_result_summary(pipeline_id: str) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    return pipeline_result_summary_payload(task, pipeline_id)


def get_pipeline_frame_detail(pipeline_id: str, frame: int) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    start_frame, end_frame, total, _ = resolve_frame_window(task, start_frame=frame, end_frame=frame)
    if total <= 0 or start_frame != frame or end_frame != frame:
        raise HTTPException(status_code=404, detail=f"frame out of range: {frame}")

    rows = load_frame_analysis_range_records(pipeline_id, start_frame=frame, end_frame=frame)
    if not rows:
        inline_rows = task.get("report", {}).get("frame_analysis") if isinstance(task.get("report"), dict) else []
        rows = [inline_rows[frame]] if isinstance(inline_rows, list) and 0 <= frame < len(inline_rows) else []

    return pipeline_frame_detail_payload(task, pipeline_id, frame=frame, row=rows[0] if rows else None)


def get_pipeline_frame_range(
    pipeline_id: str,
    *,
    start_frame: int | None = None,
    end_frame: int | None = None,
    start_sec: float | None = None,
    end_sec: float | None = None,
) -> dict[str, Any]:
    task = _get_task(pipeline_id)
    resolved_start, resolved_end, total, teacher_fps = resolve_frame_window(
        task,
        start_frame=start_frame,
        end_frame=end_frame,
        start_sec=start_sec,
        end_sec=end_sec,
    )

    rows: list[dict[str, Any]] = []
    if total > 0 and resolved_end >= resolved_start:
        rows = load_frame_analysis_range_records(
            pipeline_id,
            start_frame=resolved_start,
            end_frame=resolved_end,
        )
        if not rows:
            inline_rows = task.get("report", {}).get("frame_analysis") if isinstance(task.get("report"), dict) else []
            rows = inline_rows[resolved_start : resolved_end + 1] if isinstance(inline_rows, list) else []

    return pipeline_frame_range_payload(
        task,
        pipeline_id,
        start_frame=resolved_start,
        end_frame=resolved_end,
        total=total,
        teacher_fps=teacher_fps,
        rows=rows,
    )


def get_pipeline_failure_stats(days: int = 30, limit: int = 20) -> dict[str, Any]:
    return load_pipeline_failure_stats(days=days, limit=limit)
