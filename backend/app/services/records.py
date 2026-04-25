from __future__ import annotations

from app.services.pipeline import get_analysis_report, list_analysis_reports, list_pipeline_tasks
from app.services.record_issue_index import load_or_build_record_issue_index


def _latest_time(item: dict) -> str:
    return str(item.get("updated_at") or item.get("finished_at") or item.get("started_at") or item.get("queued_at") or "")


def list_records_workspace(limit: int = 50) -> dict:
    safe_limit = max(1, min(200, int(limit)))

    task_items = list_pipeline_tasks(limit=safe_limit).get("items", [])
    report_items = list_analysis_reports(limit=safe_limit).get("items", [])

    task_map = {str(item.get("pipeline_id") or ""): item for item in task_items if item.get("pipeline_id")}
    report_map = {str(item.get("pipeline_id") or ""): item for item in report_items if item.get("pipeline_id")}
    pipeline_ids = {pipeline_id for pipeline_id in [*task_map.keys(), *report_map.keys()] if pipeline_id}

    merged_items: list[dict] = []
    for pipeline_id in pipeline_ids:
        task = task_map.get(pipeline_id) or {}
        report = report_map.get(pipeline_id) or {}
        merged_items.append(
            {
                "pipeline_id": pipeline_id,
                "pair_name": task.get("pair_name") or report.get("pair_name") or pipeline_id,
                "status": task.get("status") or report.get("status") or "done",
                "message": task.get("message"),
                "stage": task.get("stage") or report.get("stage"),
                "progress": task.get("progress"),
                "teacher_video_id": task.get("teacher_video_id") or report.get("teacher_video_id"),
                "user_video_id": task.get("user_video_id") or report.get("user_video_id"),
                "executor": task.get("executor") or report.get("executor"),
                "attempt_count": task.get("attempt_count"),
                "retry_count": task.get("retry_count"),
                "error_type": task.get("error_type"),
                "queued_at": task.get("queued_at") or report.get("queued_at"),
                "started_at": task.get("started_at") or report.get("started_at"),
                "finished_at": task.get("finished_at") or report.get("finished_at"),
                "updated_at": task.get("updated_at") or report.get("updated_at"),
                "score_total": task.get("score_total", report.get("score_total")),
                "confidence_score": task.get("confidence_score", report.get("confidence_score")),
                "cancel_requested": bool(task.get("cancel_requested")),
                "cancel_requested_at": task.get("cancel_requested_at"),
                "timeout_sec": task.get("timeout_sec"),
                "timeout_at": task.get("timeout_at"),
                "score_pose": report.get("score_pose"),
                "score_tempo": report.get("score_tempo"),
                "confidence_level": report.get("confidence_level"),
                "overall_advice": report.get("overall_advice"),
                "confidence_summary": report.get("confidence_summary"),
                "beginner_summary": report.get("beginner_summary"),
                "teaching_summary": report.get("teaching_summary"),
                "top_joints": report.get("top_joints") or [],
                "files": report.get("files"),
                "has_report": bool(report),
                "issue_count": 0,
            }
        )

    merged_items.sort(key=_latest_time, reverse=True)

    issues: list[dict] = []
    for item in merged_items:
        if item.get("status") != "done":
            continue
        pipeline_id = str(item.get("pipeline_id") or "")
        if not pipeline_id:
            continue
        try:
            item_issues = load_or_build_record_issue_index(item, get_analysis_report)
        except Exception:
            continue
        issues.extend(item_issues)

    issues.sort(key=lambda item: (str(item.get("finished_at") or ""), float(item.get("sec") or 0.0)), reverse=True)

    issue_count_by_pipeline: dict[str, int] = {}
    for issue in issues:
        pipeline_id = str(issue.get("pipeline_id") or "")
        if not pipeline_id:
            continue
        issue_count_by_pipeline[pipeline_id] = issue_count_by_pipeline.get(pipeline_id, 0) + 1

    for item in merged_items:
        pipeline_id = str(item.get("pipeline_id") or "")
        item["issue_count"] = issue_count_by_pipeline.get(pipeline_id, 0)

    return {
        "items": merged_items,
        "issues": issues,
        "total": len(merged_items),
        "issue_total": len(issues),
        "limit": safe_limit,
    }
