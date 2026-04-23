from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ScoreWeights:
    pose: float = 0.45
    tempo: float = 0.25
    smooth: float = 0.20
    quality_penalty: float = 0.10


@dataclass
class PipelineConfig:
    vis_thresh: float = 0.5
    invalid_frame_quality_thr: float = 0.35
    short_gap_max: int = 6
    long_gap_quality_scale: float = 0.2

    mirror_gain_force_apply: float = 0.10

    coarse_trim_energy_q: float = 0.20
    coarse_trim_min_sec: float = 0.8

    audio_align_enabled: bool = True
    audio_align_sr: int = 2000
    audio_align_hop_sec: float = 0.02
    audio_align_max_lag_sec: float = 3.0
    audio_align_peak_floor: float = 0.10

    feature_type_default: str = "fused"
    fused_w_angle: float = 0.45
    fused_w_bone: float = 0.35
    fused_w_kin: float = 0.20

    dtw_band_ratio: float = 0.15

    map_smooth_win_sec: float = 0.8

    tempo_win_sec: float = 0.6
    tempo_fast_thr: float = 1.15
    tempo_slow_thr: float = 0.85
    tempo_min_dur_sec: float = 1.2
    tempo_conf_quality_floor: float = 0.35
    tempo_offset_tolerance_sec: float = 0.12
    tempo_offset_bad_sec: float = 0.50
    tempo_offset_smooth_win_sec: float = 0.35

    local_match_window_sec: float = 1.0
    local_match_offset_penalty: float = 0.18
    local_match_feat_weight: float = 0.65
    local_match_pose_weight: float = 0.35

    marker_min_gap_sec: float = 1.2
    marker_topk_pose: int = 10
    marker_topk_tempo: int = 6
    marker_topk_quality: int = 6

    pose_alpha: float = 2.8
    tempo_alpha: float = 2.0
    smooth_alpha: float = 1.8
    quality_penalty_scale: float = 25.0
    score_weights: ScoreWeights = field(default_factory=ScoreWeights)

    sync_seek_threshold_sec: float = 0.25
    sync_seek_cooldown_ms: int = 650
    sync_rate_min: float = 0.92
    sync_rate_max: float = 1.08
    sync_rate_gain: float = 0.35

    save_debug_plots: bool = True

    @staticmethod
    def from_obj(cfg: "PipelineConfig | dict[str, Any] | None") -> "PipelineConfig":
        if cfg is None:
            return PipelineConfig()
        if isinstance(cfg, PipelineConfig):
            return cfg
        out = PipelineConfig()
        for k, v in cfg.items():
            if k == "score_weights" and isinstance(v, dict):
                sw = out.score_weights
                for sk, sv in v.items():
                    if hasattr(sw, sk):
                        setattr(sw, sk, float(sv))
                continue
            if hasattr(out, k):
                setattr(out, k, v)
        return out

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
