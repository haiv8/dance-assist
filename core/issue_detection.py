from __future__ import annotations

import numpy as np


JOINT_CN = {
    "left_shoulder": "左肩",
    "right_shoulder": "右肩",
    "left_elbow": "左肘",
    "right_elbow": "右肘",
    "left_wrist": "左手腕",
    "right_wrist": "右手腕",
    "left_hip": "左髋",
    "right_hip": "右髋",
    "left_knee": "左膝",
    "right_knee": "右膝",
    "left_ankle": "左踝",
    "right_ankle": "右踝",
    "left_foot_index": "左脚尖",
    "right_foot_index": "右脚尖",
}


def peak_pick(curve: np.ndarray, topk: int, min_gap: int, valid_mask: np.ndarray | None = None) -> list[int]:
    x = np.nan_to_num(curve.astype(np.float64), nan=0.0)
    order = np.argsort(-x)
    out: list[int] = []
    for idx in order:
        i = int(idx)
        if valid_mask is not None and (not bool(valid_mask[i])):
            continue
        if all(abs(i - p) >= min_gap for p in out):
            out.append(i)
            if len(out) >= topk:
                break
    out.sort()
    return out


def joint_to_cn(name: str) -> str:
    return JOINT_CN.get(name, name)


def advice_for_issue(issue_type: str, joint_name: str) -> str:
    jn = joint_to_cn(joint_name)
    if issue_type == "tempo_fast":
        return f"该段节奏偏快，先把速度降下来，优先保证 {jn} 的轨迹清晰、到位再提速。"
    if issue_type == "tempo_slow":
        return f"该段节奏偏慢，建议提前准备发力点，重点提高 {jn} 的起落速度。"
    if issue_type == "tracking_bad":
        return "该段识别质量较差，建议正对镜头、增加光照并确保全身入镜后再练习。"
    return f"该段动作偏差较大，建议先分解练习 {jn}，再与上下肢连贯配合。"
