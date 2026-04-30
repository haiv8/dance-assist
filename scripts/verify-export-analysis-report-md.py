from __future__ import annotations

import importlib.util
import json
import shutil
from argparse import Namespace
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "export-analysis-report-md.py"


def _load_export_module() -> Any:
    spec = importlib.util.spec_from_file_location("export_analysis_report_md", SCRIPT_PATH)
    assert spec and spec.loader, "export-analysis-report-md.py should be importable"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    module = _load_export_module()
    temp_dir = PROJECT_ROOT / ".runtime" / "temp" / "verify-export-analysis-report-md"
    output_path = temp_dir / "out.md"

    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        report_path = temp_dir / "report.json"
        _write_json(
            report_path,
            {
                "pipeline_id": "md001",
                "scores": {"score_total": 76.5, "score_pose": 70.0},
                "confidence": {"score": 0.72},
                "score_explanation": {
                    "level": "ok",
                    "summary": "动作基本可参考",
                    "next_action": "先回看高优先级片段",
                },
                "performance": {
                    "total_sec": 3.21,
                    "stages": [{"name": "output_writing", "duration_sec": 0.1}],
                },
            },
        )
        _write_json(temp_dir / "summary.json", {"pipeline_id": "md001", "pair_name": "teacher_vs_user", "score_tempo": 82.0})
        _write_json(temp_dir / "issues.json", [{"sec": 1.2, "severity": "high", "type": "pose", "summary": "手臂角度偏差"}])

        args = Namespace(report_path=str(report_path), pipeline_id=None, output=str(output_path))
        exported = module.export_markdown(args)
        text = exported.read_text(encoding="utf-8")

        for marker in ("分析结果导出报告", "基本信息", "评分结果", "问题片段统计", "性能统计", "结论", "原始文件路径"):
            assert marker in text, f"export should include section: {marker}"
        assert "手臂角度偏差" in text, "issues should be rendered"

        minimal_report_path = temp_dir / "minimal_report.json"
        minimal_output_path = temp_dir / "minimal.md"
        _write_json(minimal_report_path, {"pipeline_id": "minimal001"})
        exported_minimal = module.export_markdown(Namespace(report_path=str(minimal_report_path), pipeline_id=None, output=str(minimal_output_path)))
        minimal_text = exported_minimal.read_text(encoding="utf-8")
        assert "--" in minimal_text or "暂无数据" in minimal_text, "missing fields should render fallback text"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("markdown export verification passed")


if __name__ == "__main__":
    main()
