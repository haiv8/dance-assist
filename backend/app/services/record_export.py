from __future__ import annotations

import csv
import io
from typing import Any

from app.services.records import list_records_workspace
from app.services.task_store_reports import load_output_summary


CSV_FIELDS = [
    "pipeline_id",
    "pair_name",
    "teacher_video_id",
    "user_video_id",
    "status",
    "score_total",
    "score_pose",
    "score_tempo",
    "confidence_score",
    "confidence_level",
    "issue_count",
    "high_issue_count",
    "total_sec",
    "finished_at",
    "created_at_or_queued_at",
]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        numeric = float(value)
    except Exception:
        return _safe_text(value)
    if numeric != numeric:
        return ""
    return f"{numeric:.4f}".rstrip("0").rstrip(".")


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _status_matches(item_status: Any, status: str | None) -> bool:
    if not status:
        return True
    return str(item_status or "").strip() == status


def _starred_matches(item: dict[str, Any], starred: bool | None) -> bool:
    if starred is None:
        return True
    return bool(item.get("starred")) is starred


def _performance_total_sec(item: dict[str, Any], summary: dict[str, Any]) -> str:
    status = item.get("status")
    if str(status or "") != "done":
        return ""
    performance = summary.get("performance") if isinstance(summary, dict) else None
    if not isinstance(performance, dict):
        return ""
    return _safe_number(performance.get("total_sec"))


def build_records_csv(*, limit: int = 200, starred: bool | None = None, status: str | None = None) -> str:
    safe_limit = max(1, min(500, int(limit)))
    task_status = status if status in {"done", "failed", "running"} else None
    workspace = list_records_workspace(limit=safe_limit)
    items = [item for item in workspace.get("items", []) if isinstance(item, dict)]
    workspace_issues = [issue for issue in workspace.get("issues", []) if isinstance(issue, dict)]

    high_issue_count_by_pipeline: dict[str, int] = {}
    for issue in workspace_issues:
        if str(issue.get("severity") or "").lower() != "high":
            continue
        pipeline_id = str(issue.get("pipeline_id") or "")
        if pipeline_id:
            high_issue_count_by_pipeline[pipeline_id] = high_issue_count_by_pipeline.get(pipeline_id, 0) + 1

    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pipeline_id = str(item.get("pipeline_id") or "")
        if not _status_matches(item.get("status"), task_status):
            continue
        if not _starred_matches(item, starred):
            continue

        summary = load_output_summary(str(item.get("pair_name") or "").strip())
        rows.append(
            {
                "pipeline_id": pipeline_id,
                "pair_name": _safe_text(item.get("pair_name")),
                "teacher_video_id": _safe_text(item.get("teacher_video_id")),
                "user_video_id": _safe_text(item.get("user_video_id")),
                "status": _safe_text(item.get("status")),
                "score_total": _safe_number(_first_present(item.get("score_total"), summary.get("score_total"))),
                "score_pose": _safe_number(summary.get("score_pose")),
                "score_tempo": _safe_number(summary.get("score_tempo")),
                "confidence_score": _safe_number(_first_present(item.get("confidence_score"), summary.get("confidence_score"))),
                "confidence_level": _safe_text(item.get("confidence_level") or summary.get("confidence_level")),
                "issue_count": _safe_number(item.get("issue_count")),
                "high_issue_count": _safe_number(high_issue_count_by_pipeline.get(pipeline_id, 0)),
                "total_sec": _performance_total_sec(item, summary) if pipeline_id else "",
                "finished_at": _safe_text(item.get("finished_at")),
                "created_at_or_queued_at": _safe_text(item.get("created_at") or item.get("queued_at")),
            }
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    # UTF-8 BOM helps Excel on Windows open Chinese text without mojibake.
    return "\ufeff" + output.getvalue()
