from __future__ import annotations

import csv
import importlib.util
import io
import json
import shutil
from argparse import Namespace
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "summarize-thesis-experiments.py"


def _load_summary_module() -> Any:
    spec = importlib.util.spec_from_file_location("summarize_thesis_experiments", SCRIPT_PATH)
    assert spec and spec.loader, "summarize-thesis-experiments.py should be importable"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_result(root: Path, name: str, *, sample_type: str, score: float | None, confidence: float | None, issues: list[dict[str, Any]], total_sec: float | None) -> None:
    pair_dir = root / name
    pair_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "pipeline_id": name,
        "pair_name": name,
        "teacher_video_id": "teacher_ref",
        "user_video_id": f"user_{sample_type}",
        "scores": {
            "score_total": score,
            "score_pose": 70.0 if score is not None else None,
            "score_tempo": 80.0 if score is not None else None,
        },
        "confidence": {"score": confidence, "level": "low" if confidence is not None and confidence < 0.55 else "medium"},
        "performance": {
            "total_sec": total_sec,
            "stages": [
                {"name": "feature_building", "duration_sec": 1.2},
                {"name": "alignment_dtw", "duration_sec": 2.5},
                {"name": "output_writing", "duration_sec": 0.2},
            ],
        },
        "finished_at": "2026-05-01T12:00:00Z",
    }
    summary = {
        "pipeline_id": name,
        "pair_name": name,
        "teacher_video_id": "teacher_ref",
        "user_video_id": f"user_{sample_type}",
        "score_total": score,
        "confidence_score": confidence,
        "finished_at": "2026-05-01T12:00:00Z",
    }
    _write_json(pair_dir / "report.json", report)
    _write_json(pair_dir / "summary.json", summary)
    _write_json(pair_dir / "issues.json", issues)


def main() -> None:
    module = _load_summary_module()
    temp_dir = PROJECT_ROOT / ".runtime" / "temp" / "verify-thesis-summary-export"
    outputs_dir = temp_dir / "outputs"
    export_dir = temp_dir / "exports"
    manifest_path = temp_dir / "manifest.json"

    shutil.rmtree(temp_dir, ignore_errors=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    try:
        _make_result(
            outputs_dir,
            "pipeline_user_original",
            sample_type="original",
            score=82.5,
            confidence=0.86,
            total_sec=5.4,
            issues=[
                {"sec": 1.1, "severity": "high", "type": "pose", "summary": "手臂角度偏差"},
                {"sec": 2.0, "severity": "medium", "type": "tempo", "summary": "节奏略慢"},
            ],
        )
        _make_result(
            outputs_dir,
            "pipeline_user_low_quality_480p",
            sample_type="low_quality",
            score=None,
            confidence=0.42,
            total_sec=6.8,
            issues=[{"sec": 0.8, "severity": "high", "type": "confidence", "summary": "跟踪质量偏低"}],
        )
        _make_result(
            outputs_dir,
            "pipeline_missing_fields",
            sample_type="unknown",
            score=None,
            confidence=None,
            total_sec=None,
            issues=[],
        )

        _write_json(
            manifest_path,
            {
                "samples": [
                    {"sample_id": "user_original", "type": "original", "path": "thesis_exp_user_original.mp4", "description": "原始样例"},
                    {"sample_id": "user_low_quality_480p", "type": "low_quality", "path": "thesis_exp_user_low_quality_480p.mp4", "description": "低质量样例"},
                ]
            },
        )

        csv_path, md_path = module.export_summary(
            Namespace(
                outputs_dir=str(outputs_dir),
                pipeline_id=None,
                manifest=str(manifest_path),
                output_dir=str(export_dir),
            )
        )

        csv_text = csv_path.read_text(encoding="utf-8")
        assert csv_text.startswith("\ufeff"), "CSV should include UTF-8 BOM"
        for marker in ("pipeline_id", "score_total", "confidence_score", "issue_count", "high_issue_count", "total_sec", "slowest_stage"):
            assert marker in csv_text, f"CSV should contain {marker}"

        rows = list(csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))))
        assert len(rows) == 3, "all constructed results should be summarized"
        original = next(row for row in rows if row["pipeline_id"] == "pipeline_user_original")
        assert original["score_total"] == "82.5"
        assert original["confidence_score"] == "0.86"
        assert original["issue_count"] == "2"
        assert original["high_issue_count"] == "1"
        assert original["total_sec"] == "5.4"
        assert original["slowest_stage"] == "alignment_dtw"

        missing = next(row for row in rows if row["pipeline_id"] == "pipeline_missing_fields")
        assert missing["score_total"] == "", "missing score should export as empty value"

        md_text = md_path.read_text(encoding="utf-8")
        for marker in ("实验结果汇总表", "性能统计表", "问题片段统计表", "保守分析", "pipeline_user_low_quality_480p"):
            assert marker in md_text, f"Markdown should contain {marker}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("thesis summary export verification passed")


if __name__ == "__main__":
    main()
