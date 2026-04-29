from __future__ import annotations

from typing import Any

import numpy as np

from app.services.record_issues import (
    extract_report_issues,
    fallback_beginner_summary,
    fallback_confidence_summary,
    fallback_overall_advice,
    fallback_teaching_summary,
    normalized_confidence_issues,
    normalized_confidence_summary,
    safe_text,
)


def task_pair_name(task: dict[str, Any]) -> str:
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


def task_status(task: dict[str, Any]) -> str:
    status = task.get("status")
    if isinstance(status, str) and status in {"pending", "running", "done", "failed", "canceled"}:
        return status
    return "pending"


def task_stage(task: dict[str, Any]) -> str:
    stage = task.get("stage")
    if isinstance(stage, str) and stage.strip():
        return stage
    fallback = {
        "pending": "queued",
        "running": "processing",
        "done": "completed",
        "failed": "failed",
        "canceled": "canceled",
    }
    return fallback.get(task_status(task), "queued")


def task_score_total(task: dict[str, Any]) -> float | None:
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


def task_confidence_score(task: dict[str, Any]) -> float | None:
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


def task_progress(task: dict[str, Any]) -> float:
    try:
        progress = float(task.get("progress"))
    except Exception:
        progress = 0.0
    if not np.isfinite(progress):
        progress = 0.0
    return max(0.0, min(1.0, progress))


def report_issue_count(report: dict[str, Any]) -> int:
    confidence = report.get("confidence") if isinstance(report.get("confidence"), dict) else {}
    values = (
        report.get("markers"),
        confidence.get("issues") if isinstance(confidence, dict) else None,
        report.get("tempo_segments"),
    )
    return sum(len(value) for value in values if isinstance(value, list))


def normalize_report_text_sections(report: dict[str, Any]) -> dict[str, Any]:
    out = dict(report)
    score_total = task_score_total({"report": out})
    issue_count = report_issue_count(out)

    confidence = dict(out.get("confidence")) if isinstance(out.get("confidence"), dict) else {}
    if confidence:
        confidence["summary"] = normalized_confidence_summary(confidence)
        confidence["issues"] = normalized_confidence_issues(confidence)
        out["confidence"] = confidence

    recommendations = dict(out.get("recommendations")) if isinstance(out.get("recommendations"), dict) else {}
    recommendations["overall"] = safe_text(recommendations.get("overall"), fallback_overall_advice(score_total))
    out["recommendations"] = recommendations

    beginner_report = dict(out.get("beginner_report")) if isinstance(out.get("beginner_report"), dict) else {}
    beginner_report["summary"] = safe_text(
        beginner_report.get("summary"),
        fallback_beginner_summary(score_total, issue_count),
    )
    out["beginner_report"] = beginner_report

    teaching_report = dict(out.get("teaching_report")) if isinstance(out.get("teaching_report"), dict) else {}
    teaching_report["summary"] = safe_text(
        teaching_report.get("summary"),
        fallback_teaching_summary(score_total, issue_count),
    )
    out["teaching_report"] = teaching_report

    return out


def task_summary(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": str(task.get("pipeline_id", "") or ""),
        "pair_name": task_pair_name(task),
        "status": task_status(task),
        "message": task.get("message"),
        "stage": task_stage(task),
        "progress": task_progress(task),
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
        "score_total": task_score_total(task),
        "confidence_score": task_confidence_score(task),
        "cancel_requested": bool(task.get("cancel_requested")),
        "cancel_requested_at": task.get("cancel_requested_at"),
        "timeout_sec": task.get("timeout_sec"),
        "timeout_at": task.get("timeout_at"),
    }


def summarize_report(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(report, dict):
        return report

    out = normalize_report_text_sections({k: v for k, v in report.items() if k != "frame_analysis"})
    rows = report.get("frame_analysis")
    if isinstance(rows, list):
        out["frame_analysis_count"] = len(rows)
    return out


def summarize_timeline(timeline: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(timeline, dict):
        return timeline

    out: dict[str, Any] = {}
    heavy_arrays = {"map_user_sec", "teacher_to_user", "frame_quality"}
    marker_arrays = {"marker_frames", "marker_types"}

    for key, value in timeline.items():
        if key in heavy_arrays and isinstance(value, list):
            out[f"{key}_count"] = len(value)
            if value:
                out[f"{key}_preview"] = [value[0], value[min(len(value) - 1, len(value) // 2)], value[-1]]
            continue

        if key in marker_arrays and isinstance(value, list):
            out[f"{key}_count"] = len(value)
            out[key] = value[:200]
            continue

        out[key] = value

    return out


def frame_analysis_rows(task: dict[str, Any]) -> list[dict[str, Any]]:
    report = task.get("report")
    rows = report.get("frame_analysis") if isinstance(report, dict) else None
    return rows if isinstance(rows, list) else []


def frame_analysis_count(task: dict[str, Any]) -> int:
    report = task.get("report")
    if isinstance(report, dict):
        try:
            count = int(report.get("frame_analysis_count"))
        except Exception:
            count = 0
        if count > 0:
            return count
    return len(frame_analysis_rows(task))


def fps_teacher(task: dict[str, Any]) -> float:
    timeline = task.get("timeline") if isinstance(task.get("timeline"), dict) else {}
    report = task.get("report") if isinstance(task.get("report"), dict) else {}
    for raw in (timeline.get("fps_teacher"), report.get("fps_teacher"), 30):
        try:
            value = float(raw)
        except Exception:
            continue
        if np.isfinite(value) and value > 0:
            return value
    return 30.0


def resolve_frame_window(
    task: dict[str, Any],
    *,
    start_frame: int | None = None,
    end_frame: int | None = None,
    start_sec: float | None = None,
    end_sec: float | None = None,
) -> tuple[int, int, int, float]:
    total = frame_analysis_count(task)
    teacher_fps = fps_teacher(task)
    if total <= 0:
        return 0, -1, 0, teacher_fps

    resolved_start = start_frame
    resolved_end = end_frame
    if start_sec is not None:
        resolved_start = int(max(0.0, float(start_sec)) * teacher_fps)
    if end_sec is not None:
        resolved_end = int(max(0.0, float(end_sec)) * teacher_fps)

    if resolved_start is None and resolved_end is None:
        resolved_start = 0
        resolved_end = min(total - 1, 120)
    elif resolved_start is None:
        resolved_end = max(0, int(resolved_end))
        resolved_start = resolved_end
    elif resolved_end is None:
        resolved_start = max(0, int(resolved_start))
        resolved_end = resolved_start
    else:
        resolved_start = max(0, int(resolved_start))
        resolved_end = max(0, int(resolved_end))

    if resolved_end < resolved_start:
        resolved_start, resolved_end = resolved_end, resolved_start

    resolved_start = max(0, min(total - 1, resolved_start))
    resolved_end = max(resolved_start, min(total - 1, resolved_end))
    return resolved_start, resolved_end, total, teacher_fps


def pipeline_status_payload(task: dict[str, Any], pipeline_id: str) -> dict[str, Any]:
    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": task_pair_name(task),
        "status": task_status(task),
        "message": task.get("message"),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "updated_at": task.get("updated_at"),
        "executor": task.get("executor"),
        "attempt_count": task.get("attempt_count"),
        "retry_count": task.get("retry_count"),
        "error_type": task.get("error_type"),
        "stage": task_stage(task),
        "progress": task_progress(task),
        "cancel_requested": bool(task.get("cancel_requested")),
        "cancel_requested_at": task.get("cancel_requested_at"),
        "timeout_sec": task.get("timeout_sec"),
        "timeout_at": task.get("timeout_at"),
    }


def pipeline_result_payload(task: dict[str, Any], pipeline_id: str) -> dict[str, Any]:
    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": task_pair_name(task),
        "status": task_status(task),
        "message": task.get("message"),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "updated_at": task.get("updated_at"),
        "executor": task.get("executor"),
        "attempt_count": task.get("attempt_count"),
        "retry_count": task.get("retry_count"),
        "error_type": task.get("error_type"),
        "stage": task_stage(task),
        "progress": task_progress(task),
        "cancel_requested": bool(task.get("cancel_requested")),
        "cancel_requested_at": task.get("cancel_requested_at"),
        "timeout_sec": task.get("timeout_sec"),
        "timeout_at": task.get("timeout_at"),
        "report": task.get("report"),
        "timeline": task.get("timeline"),
        "files": task.get("files"),
    }


def pipeline_result_summary_payload(task: dict[str, Any], pipeline_id: str) -> dict[str, Any]:
    report_payload = task.get("report") if isinstance(task.get("report"), dict) else None
    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": task_pair_name(task),
        "status": task_status(task),
        "message": task.get("message"),
        "queued_at": task.get("queued_at"),
        "started_at": task.get("started_at"),
        "finished_at": task.get("finished_at"),
        "updated_at": task.get("updated_at"),
        "executor": task.get("executor"),
        "attempt_count": task.get("attempt_count"),
        "retry_count": task.get("retry_count"),
        "error_type": task.get("error_type"),
        "stage": task_stage(task),
        "progress": task_progress(task),
        "cancel_requested": bool(task.get("cancel_requested")),
        "cancel_requested_at": task.get("cancel_requested_at"),
        "timeout_sec": task.get("timeout_sec"),
        "timeout_at": task.get("timeout_at"),
        "report": summarize_report(report_payload),
        "score_explanation": (
            report_payload.get("score_explanation")
            if isinstance(report_payload, dict) and isinstance(report_payload.get("score_explanation"), dict)
            else None
        ),
        "timeline": summarize_timeline(task.get("timeline")),
        "files": task.get("files"),
        "issues": extract_report_issues(
            {
                "pipeline_id": task.get("pipeline_id", pipeline_id),
                "pair_name": task_pair_name(task),
                "teacher_video_id": task.get("teacher_video_id"),
                "user_video_id": task.get("user_video_id"),
                "finished_at": task.get("finished_at"),
                "updated_at": task.get("updated_at"),
                "score_total": task_score_total(task),
                "confidence_score": task_confidence_score(task),
                "confidence_summary": (
                    report_payload.get("confidence", {}).get("summary")
                    if isinstance(report_payload, dict) and isinstance(report_payload.get("confidence"), dict)
                    else None
                ),
                "report": report_payload or {},
            }
        ),
    }


def pipeline_frame_detail_payload(
    task: dict[str, Any],
    pipeline_id: str,
    *,
    frame: int,
    row: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": task_pair_name(task),
        "status": task_status(task),
        "frame": frame,
        "frame_analysis": row,
    }


def pipeline_frame_range_payload(
    task: dict[str, Any],
    pipeline_id: str,
    *,
    start_frame: int,
    end_frame: int,
    total: int,
    teacher_fps: float,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for offset, row in enumerate(rows):
        row_frame = row.get("frame") if isinstance(row, dict) else None
        try:
            frame_value = int(row_frame)
        except Exception:
            frame_value = start_frame + offset
        sec_value = row.get("sec") if isinstance(row, dict) else None
        try:
            sec_float = float(sec_value) if sec_value is not None else frame_value / max(1e-6, teacher_fps)
        except Exception:
            sec_float = frame_value / max(1e-6, teacher_fps)
        items.append(
            {
                "frame": frame_value,
                "sec": sec_float,
                "frame_analysis": row if isinstance(row, dict) else None,
            }
        )

    return {
        "pipeline_id": task.get("pipeline_id", pipeline_id),
        "pair_name": task_pair_name(task),
        "status": task_status(task),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "total": total,
        "fps_teacher": teacher_fps,
        "items": items,
    }


def analysis_report_fallback_item(item: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    raw_report = task.get("report") if isinstance(task.get("report"), dict) else {}
    report = normalize_report_text_sections(raw_report)
    confidence = report.get("confidence") if isinstance(report, dict) else {}
    recommendations = report.get("recommendations") if isinstance(report, dict) else {}
    beginner_report = report.get("beginner_report") if isinstance(report, dict) else {}
    teaching_report = report.get("teaching_report") if isinstance(report, dict) else {}
    scores = report.get("scores") if isinstance(report, dict) else {}
    return {
        **item,
        "score_pose": scores.get("score_pose") if isinstance(scores, dict) else None,
        "score_tempo": scores.get("score_tempo") if isinstance(scores, dict) else None,
        "confidence_level": confidence.get("level") if isinstance(confidence, dict) else None,
        "overall_advice": recommendations.get("overall") if isinstance(recommendations, dict) else fallback_overall_advice(item.get("score_total")),
        "confidence_summary": (
            confidence.get("summary")
            if isinstance(confidence, dict)
            else fallback_confidence_summary(item.get("confidence_score"))
        ),
        "beginner_summary": (
            beginner_report.get("summary")
            if isinstance(beginner_report, dict)
            else fallback_beginner_summary(item.get("score_total"), 0)
        ),
        "teaching_summary": (
            teaching_report.get("summary")
            if isinstance(teaching_report, dict)
            else fallback_teaching_summary(item.get("score_total"), 0)
        ),
        "top_joints": report.get("top_joints") if isinstance(report.get("top_joints"), list) else [],
        "score_explanation": report.get("score_explanation") if isinstance(report.get("score_explanation"), dict) else None,
        "files": task.get("files") if isinstance(task.get("files"), dict) else {},
    }


def analysis_report_payload_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    raw_report = summary.get("report") if isinstance(summary.get("report"), dict) else {}
    report = normalize_report_text_sections(raw_report)
    confidence = report.get("confidence") if isinstance(report, dict) else {}
    recommendations = report.get("recommendations") if isinstance(report, dict) else {}
    beginner_report = report.get("beginner_report") if isinstance(report, dict) else {}
    teaching_report = report.get("teaching_report") if isinstance(report, dict) else {}
    scores = report.get("scores") if isinstance(report, dict) else {}
    return {
        **summary,
        "teacher_video_id": None,
        "user_video_id": None,
        "score_total": task_score_total({"report": report}),
        "score_pose": scores.get("score_pose") if isinstance(scores, dict) else None,
        "score_tempo": scores.get("score_tempo") if isinstance(scores, dict) else None,
        "confidence_score": task_confidence_score({"report": report}),
        "confidence_level": confidence.get("level") if isinstance(confidence, dict) else None,
        "overall_advice": recommendations.get("overall") if isinstance(recommendations, dict) else None,
        "confidence_summary": confidence.get("summary") if isinstance(confidence, dict) else None,
        "beginner_summary": beginner_report.get("summary") if isinstance(beginner_report, dict) else None,
        "teaching_summary": teaching_report.get("summary") if isinstance(teaching_report, dict) else None,
        "top_joints": report.get("top_joints") if isinstance(report.get("top_joints"), list) else [],
        "score_explanation": report.get("score_explanation") if isinstance(report.get("score_explanation"), dict) else None,
    }
