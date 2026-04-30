from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _latest_performance_report() -> tuple[dict[str, Any], Path] | None:
    candidates: list[Path] = []
    for root in [PROJECT_ROOT / "outputs", PROJECT_ROOT / ".runtime" / "outputs"]:
        if root.exists():
            candidates.extend(root.rglob("report.json"))
    if not candidates:
        return None

    for path in sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("performance"), dict):
            return payload, path
    return None


def _sample_report() -> dict[str, Any]:
    return {
        "performance": {
            "total_sec": 0.0,
            "stages": [
                {"name": "input_prepare", "duration_sec": 0.0},
                {"name": "output_writing", "duration_sec": 0.0},
            ],
        },
    }


def _is_non_negative_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except Exception:
        return False
    return number >= 0 and number == number


def verify_performance(report: dict[str, Any]) -> None:
    performance = report.get("performance")
    assert isinstance(performance, dict), "performance must exist and be an object"
    assert _is_non_negative_number(performance.get("total_sec")), "performance.total_sec must be a non-negative number"

    stages = performance.get("stages")
    assert isinstance(stages, list), "performance.stages must be a list"
    assert stages, "performance.stages must not be empty"

    stage_names: set[str] = set()
    for index, stage in enumerate(stages):
        assert isinstance(stage, dict), f"stage[{index}] must be an object"
        name = stage.get("name")
        assert isinstance(name, str) and name.strip(), f"stage[{index}].name must be a non-empty string"
        assert _is_non_negative_number(stage.get("duration_sec")), f"stage[{index}].duration_sec must be non-negative"
        stage_names.add(name)

    assert "output_writing" in stage_names, "performance.stages must include output_writing"


def main() -> None:
    found = _latest_performance_report()
    if found:
        report, path = found
        print(f"using report: {path}")
    else:
        report = _sample_report()
        print("using built-in sample report")
    verify_performance(report)
    print("performance verification passed")


if __name__ == "__main__":
    main()
