from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class QualityInfo:
    frame_quality: np.ndarray
    invalid_frames: np.ndarray
    low_conf_frames: np.ndarray
    long_gap_frames: np.ndarray
    joint_valid_ratio: np.ndarray


@dataclass
class AlignInfo:
    i_path: np.ndarray
    j_path: np.ndarray
    cost: float
    path_length: int
    warp_ratio: float
    jump_rate: float


@dataclass
class ScoreBreakdown:
    score_pose: float
    score_tempo: float
    score_smooth: float
    score_quality_penalty: float
    total_score: float


@dataclass
class PipelineResult:
    result_id: str
    pair_name: str
    out_dir: str
    report: dict[str, Any]
    timeline_npz: str
