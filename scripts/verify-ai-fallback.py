from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_coach import generate_ai_coach  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    summary = {
        "pipeline_id": "verify_ai_fallback",
        "pair_name": "teacher_vs_user",
        "status": "done",
        "report": {
            "score_0_100": 68.5,
            "scores": {"score_total": 68.5, "score_pose": 60.0, "score_tempo": 82.0},
            "confidence": {
                "score": 0.52,
                "level": "low",
                "summary": "当前可信度较低，建议结合视频回看。",
            },
            "recommendations": {"overall": "先处理高误差动作片段。"},
        },
        "issues": [
            {
                "type": "pose_error",
                "severity": "high",
                "sec": 1.2,
                "summary": "手臂轨迹偏差较大",
                "action": "先慢速拆解手臂路线。",
            }
        ],
    }

    with patch("app.services.ai_coach.settings.AI_PROVIDER", "local"):
        result = generate_ai_coach(summary)

    assert_true(result["generated_by"] == "local_fallback", "missing API key/local provider should use local fallback")
    assert_true(result["summary"], "fallback should generate summary")
    assert_true(result["priority_issues"], "fallback should generate priority issues")
    assert_true(result["practice_plan"], "fallback should generate practice plan")

    payload_text = " ".join(
        [
            str(result.get("summary") or ""),
            str(result.get("setup_hint") or ""),
            str(result.get("safety_note") or ""),
            " ".join(str(note) for note in result.get("teacher_notes") or []),
        ]
    )
    assert_true("结构化分析报告" in payload_text, "fallback should say it is based on structured report data")
    assert_true("不参与动作评分" in payload_text, "fallback should clarify AI does not score actions")

    print("ai fallback verification passed")
    print(f"summary={result['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
