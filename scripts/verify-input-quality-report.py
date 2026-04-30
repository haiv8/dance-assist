from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.pipeline import _attach_input_quality  # noqa: E402


INPUT_QUALITY = {
    "level": "warning",
    "summary": "学员视频分辨率偏低",
    "teacher_meta": {"duration_sec": 39.2, "width": 1920, "height": 1080, "fps": 30},
    "user_meta": {"duration_sec": 39.6, "width": 480, "height": 360, "fps": 25},
    "checks": [{"key": "resolution", "level": "warning", "message": "分辨率偏低"}],
    "recommendations": ["建议使用更清晰的视频重新分析"],
}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    temp_dir = PROJECT_ROOT / ".tmp_verify_input_quality_report"
    shutil.rmtree(temp_dir, ignore_errors=True)

    try:
        pair_dir = temp_dir / "with-summary"
        pair_dir.mkdir(parents=True, exist_ok=True)
        _write_json(pair_dir / "report.json", {"pipeline_id": "quality001"})
        _write_json(pair_dir / "summary.json", {"pipeline_id": "quality001"})

        report = _read_json(pair_dir / "report.json")
        returned = _attach_input_quality(pair_dir, report, INPUT_QUALITY)
        assert isinstance(returned, dict), "dict report should be returned as dict"

        persisted_report = _read_json(pair_dir / "report.json")
        persisted_summary = _read_json(pair_dir / "summary.json")
        assert "input_quality" in persisted_report, "report.json should contain input_quality"
        assert persisted_report["input_quality"]["level"] == "warning", "report input_quality level should be warning"
        assert "input_quality_level" in persisted_summary, "summary.json should contain input_quality_level"
        assert "input_quality_summary" in persisted_summary, "summary.json should contain input_quality_summary"
        assert persisted_summary["input_quality_level"] == "warning", "summary input_quality_level should be warning"
        assert persisted_summary["input_quality_summary"] == "学员视频分辨率偏低", "summary input_quality_summary should match"

        no_summary_dir = temp_dir / "without-summary"
        no_summary_dir.mkdir(parents=True, exist_ok=True)
        _write_json(no_summary_dir / "report.json", {"pipeline_id": "quality002"})
        no_summary_report = _read_json(no_summary_dir / "report.json")
        _attach_input_quality(no_summary_dir, no_summary_report, INPUT_QUALITY)
        assert _read_json(no_summary_dir / "report.json")["input_quality"]["level"] == "warning"
        assert not (no_summary_dir / "summary.json").exists(), "missing summary.json should not be created"

        invalid_report = ["not", "a", "dict"]
        returned_invalid = _attach_input_quality(temp_dir / "invalid-report", invalid_report, INPUT_QUALITY)
        assert returned_invalid is invalid_report, "non-dict report should be returned unchanged"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("input quality report verification passed")


if __name__ == "__main__":
    main()
