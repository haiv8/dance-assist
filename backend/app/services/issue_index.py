from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from app.services.record_issues import extract_report_issues
from app.settings import settings


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())


def _pair_name_from_artifact_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    parsed = urlparse(value.strip())
    path_parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] == "artifacts":
        return path_parts[1]
    return ""


def _pair_name_from_source(source: Any) -> str:
    if isinstance(source, dict):
        pair_name = str(source.get("pair_name") or "").strip()
        if pair_name:
            return pair_name
        files = source.get("files") if isinstance(source.get("files"), dict) else {}
        for key in ("issues_url", "report_url", "summary_url", "timeline_json_url"):
            pair_name = _pair_name_from_artifact_url(files.get(key))
            if pair_name:
                return pair_name
    return ""


def _pipeline_id_from_source(source: Any) -> str:
    if isinstance(source, dict):
        return str(source.get("pipeline_id") or "").strip()
    if isinstance(source, str):
        return source.strip()
    return ""


def issue_index_path(source: Any) -> Path:
    candidates = issue_index_candidate_paths(source)
    if candidates:
        return candidates[0]

    pipeline_id = _pipeline_id_from_source(source)
    safe_id = _safe_name(pipeline_id or "unknown")
    return settings.DATA_DIR / "record_issues" / safe_id / "issues.json"


def _legacy_issue_index_path(source: Any) -> Path | None:
    pipeline_id = _pipeline_id_from_source(source)
    if not pipeline_id:
        return None
    return settings.DATA_DIR / "record_issues" / f"{_safe_name(pipeline_id)}.json"


def _append_unique_path(paths: list[Path], path: Path) -> None:
    if path not in paths:
        paths.append(path)


def issue_index_candidate_paths(source: Any) -> list[Path]:
    paths: list[Path] = []

    if isinstance(source, dict):
        pair_name = _pair_name_from_source(source)
        if pair_name:
            _append_unique_path(paths, settings.OUTPUTS_DIR / pair_name / "issues.json")

        files = source.get("files") if isinstance(source.get("files"), dict) else {}
        for key in ("issues_url", "report_url", "summary_url"):
            pair_name = _pair_name_from_artifact_url(files.get(key))
            if pair_name:
                _append_unique_path(paths, settings.OUTPUTS_DIR / pair_name / "issues.json")

    pipeline_id = _pipeline_id_from_source(source)
    if pipeline_id:
        safe_id = _safe_name(pipeline_id)
        _append_unique_path(paths, settings.DATA_DIR / "record_issues" / safe_id / "issues.json")
        legacy_path = _legacy_issue_index_path(source)
        if legacy_path is not None:
            _append_unique_path(paths, legacy_path)

    return paths


def build_issue_index_from_report(report_detail: dict[str, Any]) -> list[dict[str, Any]]:
    return extract_report_issues(report_detail if isinstance(report_detail, dict) else {})


def save_issue_index(report_detail: dict[str, Any]) -> list[dict[str, Any]]:
    issues = build_issue_index_from_report(report_detail)
    path = issue_index_path(report_detail)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return issues


def load_issue_index(source: Any) -> list[dict[str, Any]] | None:
    for path in issue_index_candidate_paths(source):
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if isinstance(payload, list):
            return [issue for issue in payload if isinstance(issue, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("issues"), list):
            return [issue for issue in payload["issues"] if isinstance(issue, dict)]
    return None


def load_or_build_issue_index(source: dict[str, Any], report_loader: Callable[[str], dict[str, Any]]) -> list[dict[str, Any]]:
    cached = load_issue_index(source)
    if cached is not None:
        return cached

    pipeline_id = str(source.get("pipeline_id") or "").strip()
    if not pipeline_id:
        return []
    report = report_loader(pipeline_id)
    return save_issue_index(report)


def delete_issue_index(source: Any) -> bool:
    deleted = False
    for path in issue_index_candidate_paths(source):
        try:
            path.unlink()
            deleted = True
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return deleted
