from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.practice_projects import build_practice_projects  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    records = [
        {
            "pipeline_id": "p1",
            "pair_name": "teacher_t1_vs_user_u1",
            "teacher_video_id": "t1",
            "status": "done",
            "finished_at": "2026-01-01T10:00:00",
            "score_total": 60.0,
            "score_pose": 55.0,
            "score_tempo": 70.0,
            "confidence_score": 0.7,
            "issue_count": 4,
        },
        {
            "pipeline_id": "p2",
            "pair_name": "teacher_t1_vs_user_u2",
            "teacher_video_id": "t1",
            "status": "done",
            "finished_at": "2026-01-02T10:00:00",
            "score_total": 72.0,
            "score_pose": 68.0,
            "score_tempo": 80.0,
            "confidence_score": 0.8,
            "issue_count": 2,
        },
        {
            "pipeline_id": "legacy_p",
            "pair_name": "legacy_pair",
            "status": "done",
            "finished_at": "2026-01-03T10:00:00",
            "score_total": 50.0,
            "issue_count": 1,
        },
        {"pipeline_id": "running_p", "teacher_video_id": "t1", "status": "running"},
    ]

    projects = build_practice_projects(records)
    assert_true("t1" in projects, "same teacher_video_id should aggregate into one project")
    project = projects["t1"]
    assert_true(project["analysis_count"] == 2, "project should count completed records only")
    assert_true(project["latest_score"] == 72.0, "latest score should use latest finished record")
    assert_true(project["best_score"] == 72.0, "best score should be max score")
    assert_true(project["avg_score"] == 66.0, "avg score should be mean score")
    assert_true(project["issue_total"] == 6, "issue total should sum issue_count")
    assert_true(len(project["trend"]) == 2, "trend should include one point per completed record")
    assert_true(project["trend"][0]["pipeline_id"] == "p1", "trend should be chronological")

    legacy_keys = [key for key in projects if key.startswith("legacy:")]
    assert_true(legacy_keys, "records without teacher_video_id should use legacy fallback")

    print("practice projects verification passed", f"projects={len(projects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
