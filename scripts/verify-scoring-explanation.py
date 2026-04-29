from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.scoring import build_score_explanation  # noqa: E402
from core.types import ScoreBreakdown  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_explanation(
    *,
    pose: float,
    tempo: float,
    smooth: float = 72.0,
    total: float = 68.0,
    confidence_level: str = "medium",
    confidence_score: float = 0.66,
    issue_count: int = 2,
) -> dict:
    score = ScoreBreakdown(
        score_pose=pose,
        score_tempo=tempo,
        score_smooth=smooth,
        score_quality_penalty=0.0,
        total_score=total,
    )
    confidence = {
        "score": confidence_score,
        "level": confidence_level,
        "summary": "synthetic confidence",
        "issues": [],
    }
    return build_score_explanation(score, confidence, issue_count=issue_count)


def build_explanation_from_report(report: dict) -> dict:
    scores = report.get("scores") if isinstance(report.get("scores"), dict) else {}
    confidence = report.get("confidence") if isinstance(report.get("confidence"), dict) else {}
    score = ScoreBreakdown(
        score_pose=float(scores.get("score_pose") or 0.0),
        score_tempo=float(scores.get("score_tempo") or 0.0),
        score_smooth=float(scores.get("score_smooth") or 0.0),
        score_quality_penalty=float(scores.get("score_quality_penalty") or 0.0),
        total_score=float(scores.get("score_total") or report.get("score_0_100") or 0.0),
    )
    issue_count = len(report.get("markers") or [])
    return build_score_explanation(score, confidence, issue_count=issue_count)


def main() -> int:
    pose_lag_report = {
        "score_0_100": 61.0,
        "scores": {
            "score_pose": 48.0,
            "score_tempo": 86.0,
            "score_smooth": 72.0,
            "score_quality_penalty": 0.0,
            "score_total": 61.0,
        },
        "confidence": {"score": 0.42, "level": "low", "summary": "synthetic low confidence"},
        "markers": [{"type": "pose_error", "sec": 1.2}],
    }
    pose_lag = build_explanation_from_report(pose_lag_report)
    assert_true(pose_lag, "score_explanation should exist")
    assert_true(
        pose_lag["main_factor"] == "pose" or "动作" in pose_lag["summary"],
        "pose-low tempo-high case should point to pose or explain action-space deviation",
    )
    assert_true(bool(pose_lag["confidence_note"]), "confidence_note should not be empty")
    assert_true(bool(pose_lag["next_action"]), "next_action should not be empty")
    assert_true("不等同于教师评分" in pose_lag["score_note"], "score_note should explain this is not teacher scoring")

    tempo_lag_report = {
        "score_0_100": 65.0,
        "scores": {
            "score_pose": 82.0,
            "score_tempo": 55.0,
            "score_smooth": 70.0,
            "score_quality_penalty": 0.0,
            "score_total": 65.0,
        },
        "confidence": {"score": 0.7, "level": "medium", "summary": "synthetic confidence"},
    }
    tempo_lag = build_explanation_from_report(tempo_lag_report)
    assert_true(tempo_lag["main_factor"] == "tempo", "tempo-low case should point to tempo")
    assert_true("节奏" in tempo_lag["summary"], "tempo case should explain rhythm deviation")

    low_confidence = build_explanation(
        pose=72.0,
        tempo=74.0,
        confidence_level="low",
        confidence_score=0.42,
    )
    assert_true(low_confidence["main_factor"] == "confidence", "low confidence should be the main factor")
    assert_true(bool(low_confidence["confidence_note"]), "low confidence should provide confidence_note")
    assert_true("拍摄" in low_confidence["confidence_note"], "low confidence note should mention shooting conditions")

    balanced = build_explanation(pose=76.0, tempo=73.0, issue_count=0)
    assert_true(balanced["score_note"], "score_note should always exist")
    assert_true(balanced["next_action"], "next_action should always exist")

    legacy_report = {
        "score_0_100": 75.0,
        "scores": {"score_pose": 76.0, "score_tempo": 73.0, "score_total": 75.0},
        "confidence": {"score": 0.7, "level": "medium"},
    }
    legacy_fallback = build_explanation_from_report(legacy_report)
    assert_true(legacy_fallback["summary"], "legacy report fallback should not crash")

    print("scoring explanation verification passed")
    print(f"pose-low case: {pose_lag}")
    print(f"tempo-low case: {tempo_lag}")
    print(f"low-confidence case: {low_confidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
