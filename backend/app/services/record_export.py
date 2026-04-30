from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.services.issue_index import load_issue_index
from app.services.pipeline_views import task_summary
from app.services.record_flags import flag_for_record, load_record_flags
from app.services.task_store_reports import load_output_summary
from app.settings import settings


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


def _latest_time(item: dict[str, Any]) -> str:
    return str(item.get("updated_at") or item.get("finished_at") or item.get("started_at") or item.get("queued_at") or "")


def _load_task_items_from_disk(limit: int, status: str | None) -> list[dict[str, Any]]:
    tasks_dir = settings.APP_HOME / "tasks"
    if not tasks_dir.exists():
        return []

    items: list[dict[str, Any]] = []
    for path in tasks_dir.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        item = task_summary(raw)
        if status and item.get("status") != status:
            continue
        items.append(item)

    items.sort(key=_latest_time, reverse=True)
    return items[:limit]


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
    items = _load_task_items_from_disk(safe_limit, task_status)
    flags = load_record_flags()

    rows: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pipeline_id = str(item.get("pipeline_id") or "")
        flag = flag_for_record(pipeline_id, flags)
        if not _status_matches(item.get("status"), task_status):
            continue
        if not _starred_matches(flag, starred):
            continue

        summary = load_output_summary(str(item.get("pair_name") or "").strip())
        issues = load_issue_index(item) or []
        high_issue_count = sum(
            1
            for issue in issues
            if isinstance(issue, dict) and str(issue.get("severity") or "").lower() == "high"
        )
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
                "confidence_level": _safe_text(summary.get("confidence_level")),
                "issue_count": _safe_number(len(issues)),
                "high_issue_count": _safe_number(high_issue_count),
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
