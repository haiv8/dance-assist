from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services import record_export  # noqa: E402


def _workspace_sample(limit: int = 200) -> dict[str, Any]:
    return {
        "items": [
            {
                "pipeline_id": "done001",
                "pair_name": "teacher_a_vs_user_a",
                "teacher_video_id": "teacher_a",
                "user_video_id": "user_a",
                "status": "done",
                "score_total": 88.25,
                "confidence_score": 0.82,
                "confidence_level": "high",
                "issue_count": 2,
                "starred": True,
                "finished_at": "2026-05-01T10:00:00Z",
                "queued_at": "2026-05-01T09:58:00Z",
            },
            {
                "pipeline_id": "running001",
                "pair_name": "teacher_b_vs_user_b",
                "status": "running",
                "starred": False,
            },
            {
                "pipeline_id": "done_missing_fields",
                "status": "done",
            },
        ][:limit],
        "issues": [
            {"pipeline_id": "done001", "severity": "high"},
            {"pipeline_id": "done001", "severity": "medium"},
            {"pipeline_id": "done_missing_fields", "severity": "high"},
        ],
    }


def _summary_sample(pair_name: str) -> dict[str, Any]:
    if pair_name == "teacher_a_vs_user_a":
        return {
            "score_pose": 84.5,
            "score_tempo": 91.0,
            "performance": {"total_sec": 12.34},
        }
    return {}


def _rows(csv_text: str) -> list[dict[str, str]]:
    stream = io.StringIO(csv_text.lstrip("\ufeff"))
    return list(csv.DictReader(stream))


def main() -> None:
    original_workspace = record_export.list_records_workspace
    original_summary = record_export.load_output_summary
    try:
        record_export.list_records_workspace = _workspace_sample
        record_export.load_output_summary = _summary_sample

        csv_text = record_export.build_records_csv(limit=10)
        assert csv_text.startswith("\ufeff"), "CSV should include UTF-8 BOM"
        assert "pipeline_id,pair_name,teacher_video_id" in csv_text, "CSV header should be present"
        for field in ("pipeline_id", "score_total", "confidence_score", "issue_count", "high_issue_count"):
            assert field in csv_text, f"CSV should include {field}"

        rows = _rows(csv_text)
        assert len(rows) == 3, "all sample rows should be exported without filters"
        done_row = next(row for row in rows if row["pipeline_id"] == "done001")
        assert done_row["score_total"] == "88.25"
        assert done_row["confidence_score"] == "0.82"
        assert done_row["issue_count"] == "2"
        assert done_row["high_issue_count"] == "1"
        assert done_row["total_sec"] == "12.34"

        starred_rows = _rows(record_export.build_records_csv(limit=10, starred=True))
        assert [row["pipeline_id"] for row in starred_rows] == ["done001"], "starred filter should only export starred records"

        done_rows = _rows(record_export.build_records_csv(limit=10, status="done"))
        assert {row["pipeline_id"] for row in done_rows} == {"done001", "done_missing_fields"}, "status filter should only export done records"

        missing_row = next(row for row in done_rows if row["pipeline_id"] == "done_missing_fields")
        assert missing_row["pair_name"] == "", "missing text fields should export as empty strings"
        assert missing_row["score_total"] == "", "missing numeric fields should export as empty strings"
    finally:
        record_export.list_records_workspace = original_workspace
        record_export.load_output_summary = original_summary

    print("records csv export verification passed")


if __name__ == "__main__":
    main()
