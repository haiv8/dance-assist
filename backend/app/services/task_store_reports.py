from __future__ import annotations

import json
from typing import Any

from app.settings import settings


def as_db_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if out == out else None


def as_db_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def report_without_frame_analysis(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {}

    out = dict(report)
    rows = out.pop("frame_analysis", None)
    if isinstance(rows, list):
        out["frame_analysis_count"] = len(rows)
    elif "frame_analysis_count" in report:
        out["frame_analysis_count"] = report.get("frame_analysis_count")
    return out


def task_payload_for_storage(task: dict[str, Any]) -> dict[str, Any]:
    payload = dict(task)
    report = payload.get("report")
    if isinstance(report, dict):
        payload["report"] = report_without_frame_analysis(report)
    return payload


def frame_analysis_rows(task: dict[str, Any]) -> list[dict[str, Any]]:
    report = task.get("report")
    rows = report.get("frame_analysis") if isinstance(report, dict) else None
    if not isinstance(rows, list):
        return []

    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if isinstance(row, dict):
            payload = dict(row)
        else:
            payload = {"value": row}

        frame = as_db_int(payload.get("frame"))
        if frame is None:
            frame = index
        sec = as_db_float(payload.get("sec"))
        frame_error = as_db_float(payload.get("frame_error"))
        marker_type = str(payload.get("type", "")).strip() or None
        severity = str(payload.get("severity", "")).strip() or None
        payload.setdefault("frame", frame)
        if sec is not None:
            payload.setdefault("sec", sec)
        out.append(
            {
                "frame": frame,
                "sec": sec,
                "frame_error": frame_error,
                "marker_type": marker_type,
                "severity": severity,
                "payload": payload,
            }
        )
    return out


def _json_ready_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _json_ready_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def confidence_level_from_score(value: Any) -> str | None:
    score = as_db_float(value)
    if score is None:
        return None
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def load_output_summary(pair_name: str | None) -> dict[str, Any]:
    if not pair_name:
        return {}
    path = settings.OUTPUTS_DIR / str(pair_name).strip() / "summary.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def ensure_summary_url(files: dict[str, Any], pair_name: str | None) -> dict[str, Any]:
    if not pair_name:
        return dict(files)
    out = dict(files)
    if "summary_url" not in out and (settings.OUTPUTS_DIR / str(pair_name).strip() / "summary.json").exists():
        out["summary_url"] = f"/artifacts/{pair_name}/summary.json"
    return out


def derive_confidence_from_report(report: dict[str, Any], summary: dict[str, Any]) -> tuple[float | None, str | None, str | None]:
    quality = _json_ready_dict(report.get("quality_stats"))
    align = _json_ready_dict(report.get("alignment_quality"))
    tempo = _json_ready_dict(report.get("tempo"))

    teacher_invalid = as_db_float(quality.get("teacher_invalid_ratio"))
    user_invalid = as_db_float(quality.get("user_invalid_ratio"))
    teacher_low = as_db_float(quality.get("teacher_low_conf_ratio"))
    user_low = as_db_float(quality.get("user_low_conf_ratio"))
    teacher_gap = as_db_float(quality.get("teacher_long_gap_ratio"))
    user_gap = as_db_float(quality.get("user_long_gap_ratio"))
    teacher_mean = as_db_float(quality.get("teacher_mean_quality"))
    user_mean = as_db_float(quality.get("user_mean_quality"))

    if teacher_invalid is None:
        teacher_invalid = as_db_float(summary.get("quality_low_conf_ratio"))
    if user_invalid is None:
        user_invalid = teacher_invalid
    if teacher_low is None:
        teacher_low = teacher_invalid
    if user_low is None:
        user_low = teacher_low
    if teacher_gap is None:
        teacher_gap = 0.0
    if user_gap is None:
        user_gap = teacher_gap
    if teacher_mean is None:
        teacher_mean = max(0.0, min(1.0, 1.0 - (teacher_invalid or 0.0)))
    if user_mean is None:
        user_mean = max(0.0, min(1.0, 1.0 - (user_invalid or 0.0)))

    jump_rate = as_db_float(align.get("jump_rate"))
    warp_ratio = as_db_float(align.get("warp_ratio"))
    deviation_area = as_db_float(tempo.get("deviation_area"))
    fallback_linear = bool(align.get("fallback_linear_map_applied"))

    if None in (teacher_invalid, user_invalid, teacher_low, user_low, jump_rate, warp_ratio):
        return None, None, None

    tracking_quality = max(0.0, min(1.0,
        0.3 * ((teacher_mean + user_mean) / 2.0)
        + 0.4 * (1.0 - ((teacher_invalid + user_invalid) / 2.0))
        + 0.3 * (1.0 - ((teacher_low + user_low) / 2.0))
    ))

    jump_penalty = max(0.0, min(1.0, jump_rate / 0.45))
    warp_penalty = max(0.0, min(1.0, abs(warp_ratio - 1.0) / 0.9))
    alignment_stability = max(0.0, min(1.0, 1.0 - (0.7 * jump_penalty + 0.3 * warp_penalty)))
    if fallback_linear:
        alignment_stability *= 0.55

    if deviation_area is None:
        tempo_stability = 0.5
    else:
        tempo_stability = max(0.0, min(1.0, 1.0 - (deviation_area / 0.12)))

    score = max(0.0, min(1.0, 0.5 * tracking_quality + 0.3 * alignment_stability + 0.2 * tempo_stability))
    level = confidence_level_from_score(score)

    max_invalid = max(teacher_invalid, user_invalid)
    max_gap = max(teacher_gap or 0.0, user_gap or 0.0)
    notes: list[str] = []
    if max_invalid >= 0.35:
        notes.append("???????")
    elif max_invalid >= 0.22:
        notes.append("?????????")
    if max_gap >= 0.10:
        notes.append("????????")
    if fallback_linear or jump_rate >= 0.35:
        notes.append("?????????")
    if tempo_stability < 0.6:
        notes.append("?????????")

    if level == "high":
        summary_text = "??????????????????????"
    elif level == "medium":
        summary_text = "??????????????????????"
    else:
        summary_text = "????????????????????????????"

    if notes:
        summary_text = f"{summary_text} ?????{'?'.join(notes[:3])}?"

    if summary.get("confidence_summary"):
        summary_text = str(summary.get("confidence_summary"))
    if summary.get("confidence_level"):
        level = str(summary.get("confidence_level"))
    if summary.get("confidence_score") is not None:
        score = as_db_float(summary.get("confidence_score")) or score

    return score, level, summary_text


def task_report_score(task: dict[str, Any]) -> float | None:
    report = task.get("report")
    if isinstance(report, dict):
        score = report.get("score_0_100")
        if score is None:
            scores = report.get("scores")
            if isinstance(scores, dict):
                score = scores.get("score_total")
        return as_db_float(score)
    return None


def task_confidence_score(task: dict[str, Any]) -> float | None:
    report = task.get("report")
    if isinstance(report, dict):
        confidence = report.get("confidence")
        if isinstance(confidence, dict):
            return as_db_float(confidence.get("score"))
    return None


def task_report_row(task: dict[str, Any]) -> dict[str, Any] | None:
    report = _json_ready_dict(task.get("report"))
    pair_name = str(task.get("pair_name", "")).strip() or None
    summary = load_output_summary(pair_name)
    files = ensure_summary_url(_json_ready_dict(task.get("files")), pair_name)
    if not report and not files and str(task.get("status", "")).strip() != "done":
        return None

    scores = _json_ready_dict(report.get("scores"))
    confidence = _json_ready_dict(report.get("confidence"))
    recommendations = _json_ready_dict(report.get("recommendations"))
    beginner_report = _json_ready_dict(report.get("beginner_report"))
    teaching_report = _json_ready_dict(report.get("teaching_report"))

    confidence_score = task_confidence_score(task)
    if confidence_score is None:
        confidence_score = as_db_float(summary.get("confidence_score"))
    derived_score, derived_level, derived_summary = derive_confidence_from_report(report, summary)
    confidence_score = confidence_score if confidence_score is not None else derived_score

    return {
        "pipeline_id": str(task.get("pipeline_id", "")).strip(),
        "pair_name": pair_name,
        "teacher_video_id": str(task.get("teacher_video_id", "")).strip() or None,
        "user_video_id": str(task.get("user_video_id", "")).strip() or None,
        "status": str(task.get("status", "")).strip() or None,
        "stage": str(task.get("stage", "")).strip() or None,
        "executor": str(task.get("executor", "")).strip() or None,
        "queued_at": str(task.get("queued_at", "")).strip() or None,
        "started_at": str(task.get("started_at", "")).strip() or None,
        "finished_at": str(task.get("finished_at", "")).strip() or None,
        "score_total": task_report_score(task) or as_db_float(summary.get("score_total")),
        "score_pose": as_db_float(scores.get("score_pose")) or as_db_float(summary.get("score_pose")),
        "score_tempo": as_db_float(scores.get("score_tempo")) or as_db_float(summary.get("score_tempo")),
        "confidence_score": confidence_score,
        "confidence_level": str(confidence.get("level", "")).strip() or str(summary.get("confidence_level", "")).strip() or derived_level or confidence_level_from_score(confidence_score),
        "overall_advice": str(recommendations.get("overall", "")).strip() or None,
        "confidence_summary": str(confidence.get("summary", "")).strip() or str(summary.get("confidence_summary", "")).strip() or derived_summary,
        "beginner_summary": str(beginner_report.get("summary", "")).strip() or None,
        "teaching_summary": str(teaching_report.get("summary", "")).strip() or None,
        "top_joints": _json_ready_list(report.get("top_joints")),
        "files": files,
        "report_payload": report_without_frame_analysis(report),
    }


def parse_analysis_report_detail_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "pipeline_id": row[0],
        "pair_name": row[1],
        "teacher_video_id": row[2],
        "user_video_id": row[3],
        "status": row[4],
        "stage": row[5],
        "executor": row[6],
        "queued_at": row[7].isoformat() if row[7] is not None else None,
        "started_at": row[8].isoformat() if row[8] is not None else None,
        "finished_at": row[9].isoformat() if row[9] is not None else None,
        "score_total": row[10],
        "score_pose": row[11],
        "score_tempo": row[12],
        "confidence_score": row[13],
        "confidence_level": row[14] or confidence_level_from_score(row[13]),
        "overall_advice": row[15],
        "confidence_summary": row[16],
        "beginner_summary": row[17],
        "teaching_summary": row[18],
        "top_joints": json.loads(row[19]) if row[19] else [],
        "files": json.loads(row[20]) if row[20] else {},
        "report": json.loads(row[21]) if row[21] else {},
        "created_at": row[22].isoformat() if row[22] is not None else None,
        "updated_at": row[23].isoformat() if row[23] is not None else None,
    }


def parse_analysis_report_summary_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "pipeline_id": row[0],
        "pair_name": row[1],
        "teacher_video_id": row[2],
        "user_video_id": row[3],
        "status": row[4],
        "stage": row[5],
        "executor": row[6],
        "queued_at": row[7].isoformat() if row[7] is not None else None,
        "started_at": row[8].isoformat() if row[8] is not None else None,
        "finished_at": row[9].isoformat() if row[9] is not None else None,
        "score_total": row[10],
        "score_pose": row[11],
        "score_tempo": row[12],
        "confidence_score": row[13],
        "confidence_level": row[14] or confidence_level_from_score(row[13]),
        "overall_advice": row[15],
        "confidence_summary": row[16],
        "beginner_summary": row[17],
        "teaching_summary": row[18],
        "top_joints": json.loads(row[19]) if row[19] else [],
        "files": json.loads(row[20]) if row[20] else {},
        "updated_at": row[21].isoformat() if row[21] is not None else None,
    }


def parse_frame_analysis_range_rows(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for frame, sec, payload_text in rows:
        payload = json.loads(payload_text) if payload_text else {}
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("frame", int(frame))
        if sec is not None:
            payload.setdefault("sec", float(sec))
        out.append(payload)
    return out
