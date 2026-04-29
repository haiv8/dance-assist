from __future__ import annotations

import math

import numpy as np

from core.config import PipelineConfig


LM_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

MAJOR_JOINTS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
KEY_JOINTS = [11, 12, 15, 16, 23, 24, 25, 26, 27, 28]

LEFT_RIGHT_SWAP = {
    1: 4, 2: 5, 3: 6, 7: 8, 9: 10,
    11: 12, 13: 14, 15: 16, 17: 18, 19: 20, 21: 22,
    23: 24, 25: 26, 27: 28, 29: 30, 31: 32,
}
for a, b in list(LEFT_RIGHT_SWAP.items()):
    LEFT_RIGHT_SWAP[b] = a

ANGLE_TRIPLETS = [
    (11, 13, 15), (12, 14, 16),
    (23, 25, 27), (24, 26, 28),
    (13, 11, 23), (14, 12, 24),
    (11, 23, 25), (12, 24, 26),
]

BONE_PAIRS = [
    (11, 13), (13, 15), (12, 14), (14, 16),
    (23, 25), (25, 27), (24, 26), (26, 28),
    (11, 23), (12, 24), (11, 12), (23, 24),
]


def normalize_body(xyz: np.ndarray) -> np.ndarray:
    hip = 0.5 * (xyz[:, 23, :] + xyz[:, 24, :])
    sh = 0.5 * (xyz[:, 11, :] + xyz[:, 12, :])
    torso = np.linalg.norm(sh - hip, axis=1)
    scale = float(np.nanmedian(torso))
    if (not np.isfinite(scale)) or scale < 1e-6:
        scale = 1.0

    centered = (xyz - hip[:, None, :]) / scale

    # Normalize yaw by the shoulder vector on the x-z plane.
    v = centered[:, 12, :] - centered[:, 11, :]
    yaw = np.arctan2(v[:, 2], v[:, 0] + 1e-9)
    out = centered.copy()
    for i in range(centered.shape[0]):
        c = math.cos(-float(yaw[i]))
        s = math.sin(-float(yaw[i]))
        x = centered[i, :, 0]
        z = centered[i, :, 2]
        out[i, :, 0] = c * x - s * z
        out[i, :, 2] = s * x + c * z
    return out.astype(np.float32)


def mirror_xyz(xyz: np.ndarray) -> np.ndarray:
    out = xyz.copy()
    out[..., 0] *= -1.0
    idx = np.arange(33)
    for i in range(33):
        idx[i] = LEFT_RIGHT_SWAP.get(i, i)
    out = out[:, idx, :]
    return out


def angle_feature(xyz: np.ndarray) -> np.ndarray:
    feats = []
    for a, b, c in ANGLE_TRIPLETS:
        v1 = xyz[:, a, :] - xyz[:, b, :]
        v2 = xyz[:, c, :] - xyz[:, b, :]
        n1 = np.linalg.norm(v1, axis=1) + 1e-8
        n2 = np.linalg.norm(v2, axis=1) + 1e-8
        cosv = np.sum(v1 * v2, axis=1) / (n1 * n2)
        cosv = np.clip(cosv, -1.0, 1.0)
        feats.append(np.arccos(cosv))
    return np.stack(feats, axis=1).astype(np.float32)


def bone_feature(xyz: np.ndarray) -> np.ndarray:
    vecs = []
    for a, b in BONE_PAIRS:
        v = xyz[:, b, :] - xyz[:, a, :]
        n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-8
        vecs.append((v / n).astype(np.float32))
    return np.concatenate(vecs, axis=1).astype(np.float32)


def kin_feature(xyz: np.ndarray) -> np.ndarray:
    base = xyz[:, MAJOR_JOINTS, :].reshape(xyz.shape[0], -1)
    vel = np.zeros_like(base)
    vel[1:] = base[1:] - base[:-1]
    acc = np.zeros_like(base)
    acc[1:] = vel[1:] - vel[:-1]
    return np.concatenate([vel, acc], axis=1).astype(np.float32)


def build_feature(xyz_body: np.ndarray, cfg: PipelineConfig) -> tuple[np.ndarray, dict[str, int]]:
    a = angle_feature(xyz_body)
    b = bone_feature(xyz_body)
    k = kin_feature(xyz_body)

    feat = np.concatenate([
        cfg.fused_w_angle * a,
        cfg.fused_w_bone * b,
        cfg.fused_w_kin * k,
    ], axis=1).astype(np.float32)

    return feat, {"angle": a.shape[1], "bone": b.shape[1], "kin": k.shape[1], "fused": feat.shape[1]}


def motion_energy(xyz_body: np.ndarray) -> np.ndarray:
    target = xyz_body[:, [15, 16, 27, 28], :].reshape(xyz_body.shape[0], -1)
    v = np.zeros_like(target)
    v[1:] = target[1:] - target[:-1]
    return np.linalg.norm(v, axis=1)
