from __future__ import annotations

from typing import Any

import numpy as np

from core.config import PipelineConfig
from core.types import AlignInfo, QualityInfo, ScoreBreakdown


def score_alignment(
    mean_w_joint: float,
    tempo_dev_area: float,
    err_curve: np.ndarray,
    low_quality_ratio: float,
    cfg: PipelineConfig,
) -> ScoreBreakdown:
    pose = float(100.0 * np.exp(-cfg.pose_alpha * mean_w_joint))
    tempo = float(100.0 * np.exp(-cfg.tempo_alpha * tempo_dev_area))

    x = np.nan_to_num(err_curve, nan=float(np.nanmean(err_curve) if np.isfinite(np.nanmean(err_curve)) else 0.0))
    if len(x) > 2:
        d = np.diff(x)
        peaks = np.sum((d[:-1] > 0) & (d[1:] < 0))
    else:
        peaks = 0
    smooth_pen = peaks / max(1, len(x))
    smooth = float(100.0 * np.exp(-cfg.smooth_alpha * smooth_pen * 10.0))

    qpen = float(np.clip(low_quality_ratio * cfg.quality_penalty_scale * 4.0, 0.0, 100.0))

    w = cfg.score_weights
    total = w.pose * pose + w.tempo * tempo + w.smooth * smooth - w.quality_penalty * qpen

    # Poor tracking should mainly lower confidence, not automatically crush
    # the practice score unless visible motion evidence is also very weak.
    if low_quality_ratio >= 0.95:
        total = min(total, 72.0)
    elif low_quality_ratio >= 0.85:
        total = min(total, 78.0)
    elif low_quality_ratio >= 0.70:
        total = min(total, 85.0)

    total = float(np.clip(total, 0.0, 100.0))
    return ScoreBreakdown(pose, tempo, smooth, qpen, total)


def quality_snapshot(q: QualityInfo, cfg: PipelineConfig) -> dict[str, float]:
    frame_quality = np.clip(q.frame_quality.astype(np.float32), 0.0, 1.0)
    return {
        "mean_quality": float(np.mean(frame_quality)) if len(frame_quality) else 0.0,
        "invalid_ratio": float(np.mean(frame_quality < cfg.invalid_frame_quality_thr)) if len(frame_quality) else 1.0,
        "low_conf_ratio": float(np.mean(frame_quality < 0.55)) if len(frame_quality) else 1.0,
        "long_gap_ratio": float(len(q.long_gap_frames) / max(1, len(frame_quality))),
    }


def build_confidence_summary(
    teacher_quality: QualityInfo,
    user_quality: QualityInfo,
    tempo_conf: np.ndarray,
    align: AlignInfo,
    *,
    bad_alignment: bool,
    partial_alignment: dict[str, Any] | None = None,
    cfg: PipelineConfig,
) -> dict[str, Any]:
    teacher = quality_snapshot(teacher_quality, cfg)
    user = quality_snapshot(user_quality, cfg)

    tracking_quality = float(np.clip(
        0.3 * ((teacher["mean_quality"] + user["mean_quality"]) / 2.0)
        + 0.4 * (1.0 - ((teacher["invalid_ratio"] + user["invalid_ratio"]) / 2.0))
        + 0.3 * (1.0 - ((teacher["low_conf_ratio"] + user["low_conf_ratio"]) / 2.0)),
        0.0,
        1.0,
    ))

    tempo_stability = float(np.mean(np.clip(tempo_conf.astype(np.float32), 0.0, 1.0))) if len(tempo_conf) else 0.0
    jump_penalty = float(np.clip(align.jump_rate / 0.45, 0.0, 1.0))
    warp_penalty = float(np.clip(abs(align.warp_ratio - 1.0) / 0.9, 0.0, 1.0))
    alignment_stability = float(np.clip(1.0 - (0.7 * jump_penalty + 0.3 * warp_penalty), 0.0, 1.0))
    if bad_alignment:
        alignment_stability *= 0.55
    if partial_alignment and partial_alignment.get("applied"):
        teacher_coverage = float(partial_alignment.get("teacher_coverage_ratio") or 0.0)
        alignment_stability *= float(np.clip(0.65 + 0.35 * teacher_coverage, 0.35, 1.0))

    score = float(np.clip(
        0.5 * tracking_quality + 0.3 * alignment_stability + 0.2 * tempo_stability,
        0.0,
        1.0,
    ))

    if score >= 0.78:
        level = "high"
        summary = "当前结果可信度较高，关键点跟踪、动作对齐和节奏估计整体稳定，可作为本轮分析的主要参考。"
    elif score >= 0.55:
        level = "medium"
        summary = "当前结果可信度中等，整体趋势可以参考，但局部片段可能受跟踪质量或对齐稳定性影响。"
    else:
        level = "low"
        summary = "当前结果可信度较低，建议优先检查拍摄视角、遮挡和节奏同步情况，再结合视频回放谨慎解读。"

    issues: list[dict[str, Any]] = []
    if max(teacher["invalid_ratio"], user["invalid_ratio"]) >= 0.22:
        issues.append({
            "code": "tracking_coverage_low",
            "severity": "high" if max(teacher["invalid_ratio"], user["invalid_ratio"]) >= 0.35 else "medium",
            "message": "关键点覆盖率偏低，部分肢体没有被稳定识别。",
            "suggestion": "建议保证全身完整入镜、光照均匀，并尽量减少快速遮挡后再重新分析。",
        })
    if max(teacher["long_gap_ratio"], user["long_gap_ratio"]) >= 0.10:
        issues.append({
            "code": "long_occlusion_gap",
            "severity": "medium",
            "message": "存在较长时间的遮挡或关键点缺失。",
            "suggestion": "建议拉开拍摄距离，减少遮挡，确保手脚和躯干连续可见。",
        })
    if bad_alignment or align.jump_rate >= 0.35:
        issues.append({
            "code": "alignment_unstable",
            "severity": "high" if bad_alignment else "medium",
            "message": "动作对齐稳定性不足，部分片段的匹配结果可能不够可靠。",
            "suggestion": "建议检查示范与学员视频的起始时刻是否接近，并尽量保留完整连续的动作片段。",
        })
    if partial_alignment and partial_alignment.get("applied"):
        teacher_sec = partial_alignment.get("teacher_segment_sec") or [0.0, 0.0]
        teacher_coverage = float(partial_alignment.get("teacher_coverage_ratio") or 0.0)
        issues.append({
            "code": "partial_alignment_applied",
            "severity": "medium" if teacher_coverage >= 0.35 else "high",
            "message": f"系统只在老师视频 {teacher_sec[0]:.2f}-{teacher_sec[1]:.2f} 秒范围内找到可靠匹配片段。",
            "suggestion": "当前总分主要反映已匹配片段；如果希望得到整段评分，建议上传与老师视频动作范围更接近的学员片段。",
        })
    if tempo_stability < 0.60:
        issues.append({
            "code": "tempo_confidence_low",
            "severity": "medium",
            "message": "节奏估计稳定性较低，节拍相关判断需要谨慎参考。",
            "suggestion": "建议使用更清晰的原始音频，或在节奏更明确的片段重新分析。",
        })

    return {
        "score": score,
        "level": level,
        "summary": summary,
        "tracking_quality": tracking_quality,
        "alignment_stability": alignment_stability,
        "tempo_stability": tempo_stability,
        "teacher_mean_quality": teacher["mean_quality"],
        "user_mean_quality": user["mean_quality"],
        "issues": issues,
    }


def score_level(score_total: float) -> str:
    if score_total >= 85:
        return "good"
    if score_total >= 70:
        return "steady"
    if score_total >= 55:
        return "needs_practice"
    return "foundation"


def build_score_explanation(
    score: ScoreBreakdown,
    confidence_summary: dict[str, Any],
    *,
    issue_count: int = 0,
) -> dict[str, Any]:
    confidence_level = str(confidence_summary.get("level") or "")
    pose_gap = score.score_tempo - score.score_pose
    tempo_gap = score.score_pose - score.score_tempo

    main_factor = "balanced"
    if confidence_level == "low":
        main_factor = "confidence"
        if pose_gap >= 8:
            summary = "当前结果可信度偏低，分数需要结合视频回看谨慎理解；同时动作空间偏差比节奏偏差更明显。"
        elif tempo_gap >= 8:
            summary = "当前结果可信度偏低，分数需要结合视频回看谨慎理解；同时节奏偏差比动作空间偏差更明显。"
        else:
            summary = "当前结果可信度偏低，分数需要结合视频回看谨慎理解，建议先确认拍摄质量。"
    elif pose_gap >= 8:
        main_factor = "pose"
        summary = "当前总分主要受动作空间偏差影响，节奏匹配相对较好。"
    elif tempo_gap >= 8:
        main_factor = "tempo"
        summary = "当前总分主要受节奏偏差影响，动作姿态接近度相对更稳定。"
    elif score.score_smooth + 10 < max(score.score_pose, score.score_tempo):
        main_factor = "smooth"
        summary = "当前动作准确性和节奏基础尚可，但动作衔接和稳定性还有提升空间。"
    else:
        summary = "当前得分由动作准确性、节奏匹配和流畅度共同决定，建议结合问题片段复盘。"

    if confidence_level == "low":
        confidence_note = "可信度较低时，建议优先检查拍摄角度、全身入镜、光照和遮挡情况。"
        next_action = "先改善拍摄质量并结合视频回看判断，再参考高优先级问题片段。"
    elif issue_count > 0:
        confidence_note = "可信度用于说明姿态跟踪和对齐结果是否稳定，不等同于动作好坏。"
        next_action = "优先查看高优先级问题片段，再针对动作偏差或节奏偏差分段练习。"
    else:
        confidence_note = "可信度用于说明姿态跟踪和对齐结果是否稳定，不等同于动作好坏。"
        next_action = "可以从整体视频回看和重点关节开始复盘，逐步精修细节。"

    return {
        "level": score_level(float(score.total_score)),
        "summary": summary,
        "score_note": "总分综合动作准确性、节奏匹配、流畅度和质量风险；分数用于训练复盘，不等同于教师评分。",
        "confidence_note": confidence_note,
        "main_factor": main_factor,
        "next_action": next_action,
    }
