from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from core.pipeline import run as run_pipeline


@dataclass
class AlignResult:
    pair_name: str
    teacher_len: int
    user_len: int
    mean_frame_error: float
    mean_joint_error: float
    score: float
    top_joints: List[Tuple[str, float]]


def run_one_pair(root: Path, teacher: str, user: str) -> AlignResult:
    teacher_video = root / "data" / "standard_videos" / f"{teacher}.mp4"
    user_video = root / "data" / "user_videos" / f"{user}.mp4"

    if not teacher_video.exists():
        raise FileNotFoundError(f"Missing teacher video: {teacher_video}")
    if not user_video.exists():
        raise FileNotFoundError(f"Missing user video: {user_video}")

    result = run_pipeline(
        root=root,
        teacher_video_path=teacher_video,
        user_video_path=user_video,
        pair_name=f"{teacher}_vs_{user}",
    )

    report = result.report
    score = float(report.get("score_0_100", report.get("scores", {}).get("score_total", 0.0)))
    mean_joint_err = float(report.get("mean_joint_error_normcoords", 0.0))
    mean_frame_err = float(report.get("mean_feature_error", 0.0))
    top = [(str(a), float(b)) for a, b in report.get("top_joints", [])]

    return AlignResult(
        pair_name=f"{teacher} vs {user}",
        teacher_len=int(report.get("teacher_frames", 0)),
        user_len=int(report.get("user_frames", 0)),
        mean_frame_error=mean_frame_err,
        mean_joint_error=mean_joint_err,
        score=score,
        top_joints=top,
    )
