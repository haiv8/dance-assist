from __future__ import annotations

from statistics import mean
from typing import Any

from fastapi import HTTPException

from app.services.records import list_records_workspace
from app.services.storage import get_video_meta


def _sort_time(item: dict[str, Any]) -> str:
    return str(item.get("finished_at") or item.get("updated_at") or item.get("started_at") or item.get("queued_at") or "")


def _num(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _project_key(item: dict[str, Any]) -> str:
    teacher_video_id = str(item.get("teacher_video_id") or "").strip()
    if teacher_video_id:
        return teacher_video_id
    fallback = str(item.get("pair_name") or item.get("pipeline_id") or "").strip()
    return f"legacy:{fallback}" if fallback else "legacy:unknown"


def _teacher_filename(item: dict[str, Any]) -> str:
    teacher_video_id = str(item.get("teacher_video_id") or "").strip()
    if teacher_video_id:
        try:
            return str(get_video_meta(teacher_video_id, role="teacher").get("filename") or teacher_video_id)
        except Exception:
            return teacher_video_id
    return str(item.get("pair_name") or item.get("pipeline_id") or "旧记录分组")


def _trend_point(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": item.get("pipeline_id"),
        "finished_at": item.get("finished_at") or item.get("updated_at"),
        "score_total": item.get("score_total"),
        "score_pose": item.get("score_pose"),
        "score_tempo": item.get("score_tempo"),
        "confidence_score": item.get("confidence_score"),
        "issue_count": int(item.get("issue_count") or 0),
    }


def _summarize_project(key: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(items, key=_sort_time, reverse=True)
    latest = ordered[0] if ordered else {}
    scores = [_num(item.get("score_total")) for item in ordered]
    valid_scores = [score for score in scores if score is not None]
    issue_total = sum(int(item.get("issue_count") or 0) for item in ordered)
    teacher_video_id = str(latest.get("teacher_video_id") or "").strip() or key

    return {
        "teacher_video_id": teacher_video_id,
        "teacher_filename": _teacher_filename(latest),
        "analysis_count": len(ordered),
        "latest_score": _num(latest.get("score_total")),
        "best_score": max(valid_scores) if valid_scores else None,
        "avg_score": round(mean(valid_scores), 2) if valid_scores else None,
        "latest_confidence": _num(latest.get("confidence_score")),
        "latest_finished_at": latest.get("finished_at") or latest.get("updated_at"),
        "issue_total": issue_total,
        "latest_pipeline_id": latest.get("pipeline_id"),
    }


def build_practice_projects(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in records:
        if not isinstance(item, dict):
            continue
        if item.get("status") != "done":
            continue
        key = _project_key(item)
        groups.setdefault(key, []).append(item)

    projects: dict[str, dict[str, Any]] = {}
    for key, items in groups.items():
        summary = _summarize_project(key, items)
        trend = [_trend_point(item) for item in sorted(items, key=_sort_time)]
        projects[key] = {
            **summary,
            "records": sorted(items, key=_sort_time, reverse=True),
            "trend": trend,
        }
    return projects


def list_practice_projects(limit: int = 200) -> dict[str, Any]:
    workspace = list_records_workspace(limit=limit)
    projects = build_practice_projects(workspace.get("items", []))
    items = [
        {key: value for key, value in project.items() if key not in {"records", "trend"}}
        for project in projects.values()
    ]
    items.sort(key=lambda item: str(item.get("latest_finished_at") or ""), reverse=True)
    return {"items": items, "total": len(items), "limit": max(1, min(200, int(limit)))}


def get_practice_project(teacher_video_id: str, limit: int = 200) -> dict[str, Any]:
    workspace = list_records_workspace(limit=limit)
    projects = build_practice_projects(workspace.get("items", []))
    project = projects.get(teacher_video_id)
    if project is None:
        for item in projects.values():
            if item.get("teacher_video_id") == teacher_video_id:
                project = item
                break
    if project is None:
        raise HTTPException(status_code=404, detail=f"practice project not found: {teacher_video_id}")
    summary = {key: value for key, value in project.items() if key not in {"records", "trend"}}
    return {
        "project": summary,
        "records": project.get("records", []),
        "trend": project.get("trend", []),
    }
