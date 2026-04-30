from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.error_mapping import PipelineFailure, input_quality_failure, map_pipeline_exception  # noqa: E402


def _assert_type(exc: Exception, expected: str) -> None:
    payload = map_pipeline_exception(exc)
    assert payload["error_type"] == expected, f"expected {expected}, got {payload}"
    assert payload["error_message"], "error_message should be populated"
    assert payload["error_suggestion"], "error_suggestion should be populated"
    assert payload["raw_error"], "raw_error should be retained"


def _quality_type(input_quality: dict) -> str:
    return input_quality_failure(input_quality).error_type


def main() -> None:
    _assert_type(FileNotFoundError("missing video.mp4"), "video_missing")
    _assert_type(FileNotFoundError("models/pose_landmarker_full.task"), "model_missing")
    _assert_type(TimeoutError("pipeline timed out"), "timeout")

    custom = PipelineFailure(
        error_type="video_unreadable",
        error_message="自定义错误",
        error_suggestion="请重新上传视频",
        raw_error="decoder failed",
    )
    mapped = map_pipeline_exception(custom)
    assert mapped["error_type"] == "video_unreadable"
    assert mapped["error_message"] == "自定义错误"
    assert mapped["error_suggestion"] == "请重新上传视频"
    assert mapped["raw_error"] == "decoder failed"

    assert _quality_type({"summary": "missing", "checks": [{"key": "exists", "level": "error"}]}) == "video_missing"
    assert _quality_type({"summary": "unreadable", "checks": [{"key": "readable", "level": "error"}]}) == "video_unreadable"
    assert _quality_type({"summary": "ffprobe failed", "checks": [{"key": "meta", "level": "error", "message": "ffprobe executable not found"}]}) == "ffmpeg_missing"
    assert _quality_type({"summary": "too poor", "checks": [{"key": "duration", "level": "error"}]}) == "low_quality_input"

    print("error mapping verification passed")


if __name__ == "__main__":
    main()
