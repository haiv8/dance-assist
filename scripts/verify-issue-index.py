from __future__ import annotations

import tempfile
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.issue_index import (
    build_issue_index_from_report,
    issue_index_path,
    load_or_build_issue_index,
    save_issue_index,
)
from app.settings import settings


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        original_outputs_dir = settings.OUTPUTS_DIR
        original_data_dir = settings.DATA_DIR
        settings.OUTPUTS_DIR = Path(temp_dir) / "outputs"
        settings.DATA_DIR = Path(temp_dir) / "data"
        try:
            empty_report = {
                "pipeline_id": "verify_empty",
                "pair_name": "verify_empty_pair",
                "report": {},
            }
            assert build_issue_index_from_report(empty_report) == []

            report = {
                "pipeline_id": "verify_marker",
                "pair_name": "verify_marker_pair",
                "teacher_video_id": "teacher",
                "user_video_id": "user",
                "updated_at": "2026-04-25T00:00:00Z",
                "report": {
                    "markers": [
                        {"frame": 12, "sec": 1.2, "type": "pose_error", "severity": "clear"},
                    ],
                },
            }
            issues = save_issue_index(report)
            assert len(issues) == 1
            assert issue_index_path(report).name == "issues.json"
            assert issue_index_path(report).exists()

            def fail_loader(_: str) -> dict:
                raise AssertionError("report_loader should not be called when issues.json exists")

            loaded = load_or_build_issue_index(report, fail_loader)
            assert len(loaded) == 1

            legacy_dir = settings.DATA_DIR / "record_issues"
            legacy_dir.mkdir(parents=True, exist_ok=True)
            legacy_path = legacy_dir / "legacy_pipeline.json"
            legacy_path.write_text(json.dumps(issues, ensure_ascii=False), encoding="utf-8")
            assert load_or_build_issue_index({"pipeline_id": "legacy_pipeline"}, fail_loader)
        finally:
            settings.OUTPUTS_DIR = original_outputs_dir
            settings.DATA_DIR = original_data_dir

    print("issue index verification passed")


if __name__ == "__main__":
    main()
