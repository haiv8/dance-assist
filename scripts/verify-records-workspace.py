from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import records as records_service  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    task_items = [
        {
            "pipeline_id": "pipeline_done_new",
            "pair_name": "teacher_a_vs_user_a",
            "status": "done",
            "teacher_video_id": "teacher_a",
            "user_video_id": "user_a",
            "finished_at": "2026-04-25T10:00:00Z",
            "updated_at": "2026-04-25T10:01:00Z",
            "score_total": 78.5,
            "confidence_score": 0.82,
        },
        {
            "pipeline_id": "pipeline_done_old",
            "pair_name": "teacher_b_vs_user_b",
            "status": "done",
            "teacher_video_id": "teacher_b",
            "user_video_id": "user_b",
            "finished_at": "2026-04-24T10:00:00Z",
            "updated_at": "2026-04-24T10:01:00Z",
            "score_total": 62.0,
            "confidence_score": 0.5,
        },
        {
            "pipeline_id": "pipeline_running",
            "pair_name": "teacher_c_vs_user_c",
            "status": "running",
            "updated_at": "2026-04-26T10:00:00Z",
        },
    ]
    report_items = [
        {
            "pipeline_id": "pipeline_done_new",
            "pair_name": "teacher_a_vs_user_a",
            "status": "done",
            "score_pose": 80.0,
            "score_tempo": 75.0,
            "confidence_level": "high",
            "files": {"report_url": "/artifacts/teacher_a_vs_user_a/report.json"},
        }
    ]
    issue_map = {
        "pipeline_done_new": [
            {"id": "invalid_entry"},
            {"id": "new_late", "sec": 2.2, "summary": "late issue"},
            {"id": "new_early", "sec": 1.1, "summary": "early issue"},
        ],
        "pipeline_done_old": [
            {"id": "old_issue", "sec": 3.0, "summary": "old issue"},
            "bad issue payload",
        ],
    }

    def fake_load_or_build_issue_index(item: dict, report_loader) -> list:
        if item.get("pipeline_id") == "pipeline_running":
            raise AssertionError("running records should not load issues")
        return issue_map.get(str(item.get("pipeline_id")), [])

    with patch.object(records_service, "list_pipeline_tasks", return_value={"items": task_items[:2]}), \
        patch.object(records_service, "list_analysis_reports", return_value={"items": report_items}), \
        patch.object(records_service, "load_or_build_issue_index", side_effect=fake_load_or_build_issue_index):
        workspace = records_service.list_records_workspace(limit=2)

    assert_true(workspace["limit"] == 2, "limit should be preserved after clamping")
    assert_true(len(workspace["items"]) <= 2, "items should respect mocked input limit")
    assert_true("items" in workspace and "issues" in workspace, "workspace should include items and issues")

    done_new = next(item for item in workspace["items"] if item["pipeline_id"] == "pipeline_done_new")
    assert_true(done_new["issue_count"] == 3, "completed record should be associated with normalized issues")

    issue_ids = [issue.get("id") for issue in workspace["issues"]]
    assert_true("bad issue payload" not in issue_ids, "invalid issue entries should not crash or leak")
    assert_true(all(issue.get("pipeline_id") for issue in workspace["issues"]), "issues should include pipeline_id")
    assert_true(all(issue.get("pair_name") for issue in workspace["issues"]), "issues should include pair_name")
    assert_true(all("score_total" in issue for issue in workspace["issues"]), "issues should include score_total")
    assert_true(all("confidence_score" in issue for issue in workspace["issues"]), "issues should include confidence_score")

    sort_keys = [(str(issue.get("finished_at") or ""), float(issue.get("sec") or 0.0)) for issue in workspace["issues"]]
    assert_true(sort_keys == sorted(sort_keys, reverse=True), "issues should be sorted by finished_at and sec desc")

    with patch.object(records_service, "list_pipeline_tasks", return_value={"items": task_items}), \
        patch.object(records_service, "list_analysis_reports", return_value={"items": report_items}), \
        patch.object(records_service, "load_or_build_issue_index", side_effect=fake_load_or_build_issue_index):
        workspace_with_running = records_service.list_records_workspace(limit=10)
    running = next(item for item in workspace_with_running["items"] if item["pipeline_id"] == "pipeline_running")
    assert_true(running["issue_count"] == 0, "running records should not have issue count")

    print("records workspace verification passed")
    print(f"items={len(workspace['items'])}, issues={len(workspace['issues'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
