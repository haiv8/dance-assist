from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.services.record_issues import extract_report_issues
from app.settings import settings

INDEX_VERSION = 1


def _index_dir() -> Path:
    return settings.DATA_DIR / "record_issues"


def _safe_pipeline_id(pipeline_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(pipeline_id).strip())


def _index_path(pipeline_id: str) -> Path:
    safe_id = _safe_pipeline_id(pipeline_id)
    return _index_dir() / f"{safe_id}.json"


def _source_updated_at(report_or_item: dict[str, Any]) -> str:
    return str(
        report_or_item.get("updated_at")
        or report_or_item.get("finished_at")
        or report_or_item.get("started_at")
        or report_or_item.get("queued_at")
        or ""
    )


def load_record_issue_index(pipeline_id: str, *, source_updated_at: str | None = None) -> list[dict[str, Any]] | None:
    pipeline_id = str(pipeline_id).strip()
    if not pipeline_id:
        return None

    path = _index_path(pipeline_id)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("version") != INDEX_VERSION:
        return None
    if str(payload.get("pipeline_id") or "") != pipeline_id:
        return None
    if source_updated_at is not None and str(payload.get("source_updated_at") or "") != str(source_updated_at or ""):
        return None

    issues = payload.get("issues")
    if not isinstance(issues, list):
        return None
    return [issue for issue in issues if isinstance(issue, dict)]


def write_record_issue_index(report: dict[str, Any]) -> list[dict[str, Any]]:
    pipeline_id = str(report.get("pipeline_id") or "").strip()
    if not pipeline_id:
        return []

    issues = extract_report_issues(report)
    payload = {
        "version": INDEX_VERSION,
        "pipeline_id": pipeline_id,
        "source_updated_at": _source_updated_at(report),
        "issue_count": len(issues),
        "issues": issues,
    }

    directory = _index_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _index_path(pipeline_id)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return issues


def load_or_build_record_issue_index(
    item: dict[str, Any],
    report_loader: Any,
) -> list[dict[str, Any]]:
    pipeline_id = str(item.get("pipeline_id") or "").strip()
    if not pipeline_id:
        return []

    source_updated_at = _source_updated_at(item)
    cached = load_record_issue_index(pipeline_id, source_updated_at=source_updated_at)
    if cached is not None:
        return cached

    report = report_loader(pipeline_id)
    return write_record_issue_index(report)


def delete_record_issue_index(pipeline_id: str) -> bool:
    pipeline_id = str(pipeline_id).strip()
    if not pipeline_id:
        return False
    path = _index_path(pipeline_id)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
