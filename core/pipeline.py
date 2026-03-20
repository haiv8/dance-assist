from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter

from core.config import PipelineConfig
from core.io_utils import dump_json, ensure_dir, make_result_id, utc_ts
from core.types import AlignInfo, PipelineResult, QualityInfo, ScoreBreakdown

LM_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index"
]

MAJOR_JOINTS = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
KEY_JOINTS = [11, 12, 15, 16, 23, 24, 25, 26, 27, 28]

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


def _load_arr(path: Path) -> tuple[np.ndarray, np.ndarray]:
    arr = np.load(path)
    xyz = arr[..., :3].astype(np.float32)
    vis = arr[..., 3].astype(np.float32)
    vis = np.nan_to_num(vis, nan=0.0, posinf=0.0, neginf=0.0)
    vis = np.clip(vis, 0.0, 1.0).astype(np.float32)
    return xyz, vis


def _interp_short_gaps(x: np.ndarray, valid: np.ndarray, short_gap_max: int) -> np.ndarray:
    y = x.copy()
    n = len(y)
    i = 0
    while i < n:
        if valid[i]:
            i += 1
            continue
        s = i
        while i < n and (not valid[i]):
            i += 1
        e = i - 1
        gap = e - s + 1
        if gap > short_gap_max:
            continue
        l = s - 1
        r = i
        if l < 0 and r >= n:
            continue
        if l < 0:
            y[s:i] = y[r]
            continue
        if r >= n:
            y[s:i] = y[l]
            continue
        y[s:i] = np.linspace(y[l], y[r], gap + 2, dtype=np.float32)[1:-1]
    return y


def _fill_remaining_nearest(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    y = x.copy()
    if np.any(valid):
        idx = np.where(valid)[0]
        all_idx = np.arange(len(y))
        nearest = np.interp(all_idx, idx, idx)
        nearest = np.clip(np.rint(nearest).astype(np.int32), 0, len(y) - 1)
        y[~valid] = y[nearest[~valid]]
    else:
        y[:] = 0.0
    return y


def _quality_and_fill(xyz: np.ndarray, vis: np.ndarray, cfg: PipelineConfig) -> tuple[np.ndarray, QualityInfo]:
    valid = np.isfinite(vis) & (vis >= cfg.vis_thresh)
    valid_ratio = np.mean(valid, axis=1)
    key_valid_ratio = np.mean(valid[:, KEY_JOINTS], axis=1)
    frame_quality = np.clip(0.6 * valid_ratio + 0.4 * key_valid_ratio, 0.0, 1.0)

    invalid_frames = np.where(frame_quality < cfg.invalid_frame_quality_thr)[0].astype(np.int32)
    low_conf_frames = np.where(frame_quality < 0.55)[0].astype(np.int32)

    out = xyz.copy()
    long_gap_mask = np.zeros(xyz.shape[0], dtype=bool)

    for j in range(xyz.shape[1]):
        for c in range(3):
            v = valid[:, j]
            series = out[:, j, c]
            s1 = _interp_short_gaps(series, v, cfg.short_gap_max)
            valid_after = np.isfinite(s1) & v
            # mark long missing segments
            i = 0
            n = len(s1)
            while i < n:
                if v[i]:
                    i += 1
                    continue
                s = i
                while i < n and (not v[i]):
                    i += 1
                if (i - s) > cfg.short_gap_max:
                    long_gap_mask[s:i] = True
            out[:, j, c] = _fill_remaining_nearest(s1, valid_after)

    if xyz.shape[0] >= 11:
        win = 11
        for j in range(out.shape[1]):
            for c in range(3):
                out[:, j, c] = savgol_filter(out[:, j, c], window_length=win, polyorder=2)

    frame_quality = frame_quality.copy()
    frame_quality[long_gap_mask] = frame_quality[long_gap_mask] * cfg.long_gap_quality_scale

    q = QualityInfo(
        frame_quality=frame_quality.astype(np.float32),
        invalid_frames=invalid_frames,
        low_conf_frames=low_conf_frames,
        long_gap_frames=np.where(long_gap_mask)[0].astype(np.int32),
        joint_valid_ratio=np.mean(valid, axis=0).astype(np.float32),
    )
    return out, q


def _normalize_body(xyz: np.ndarray) -> np.ndarray:
    hip = 0.5 * (xyz[:, 23, :] + xyz[:, 24, :])
    sh = 0.5 * (xyz[:, 11, :] + xyz[:, 12, :])
    torso = np.linalg.norm(sh - hip, axis=1)
    scale = float(np.nanmedian(torso))
    if (not np.isfinite(scale)) or scale < 1e-6:
        scale = 1.0

    centered = (xyz - hip[:, None, :]) / scale

    # yaw normalization by shoulder vector on x-z plane
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


def _mirror_xyz(xyz: np.ndarray) -> np.ndarray:
    out = xyz.copy()
    out[..., 0] *= -1.0
    idx = np.arange(33)
    for i in range(33):
        idx[i] = LEFT_RIGHT_SWAP.get(i, i)
    out = out[:, idx, :]
    return out


def _angle_feature(xyz: np.ndarray) -> np.ndarray:
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


def _bone_feature(xyz: np.ndarray) -> np.ndarray:
    vecs = []
    for a, b in BONE_PAIRS:
        v = xyz[:, b, :] - xyz[:, a, :]
        n = np.linalg.norm(v, axis=1, keepdims=True) + 1e-8
        vecs.append((v / n).astype(np.float32))
    return np.concatenate(vecs, axis=1).astype(np.float32)


def _kin_feature(xyz: np.ndarray) -> np.ndarray:
    base = xyz[:, MAJOR_JOINTS, :].reshape(xyz.shape[0], -1)
    vel = np.zeros_like(base)
    vel[1:] = base[1:] - base[:-1]
    acc = np.zeros_like(base)
    acc[1:] = vel[1:] - vel[:-1]
    return np.concatenate([vel, acc], axis=1).astype(np.float32)


def _build_feature(xyz_body: np.ndarray, cfg: PipelineConfig) -> tuple[np.ndarray, dict[str, int]]:
    a = _angle_feature(xyz_body)
    b = _bone_feature(xyz_body)
    k = _kin_feature(xyz_body)

    feat = np.concatenate([
        cfg.fused_w_angle * a,
        cfg.fused_w_bone * b,
        cfg.fused_w_kin * k,
    ], axis=1).astype(np.float32)

    return feat, {"angle": a.shape[1], "bone": b.shape[1], "kin": k.shape[1], "fused": feat.shape[1]}


def _motion_energy(xyz_body: np.ndarray) -> np.ndarray:
    target = xyz_body[:, [15, 16, 27, 28], :].reshape(xyz_body.shape[0], -1)
    v = np.zeros_like(target)
    v[1:] = target[1:] - target[:-1]
    e = np.linalg.norm(v, axis=1)
    return e


def _trim_range(energy: np.ndarray, fps: float, cfg: PipelineConfig) -> tuple[int, int]:
    if len(energy) < 3:
        return 0, len(energy)
    thr = float(np.quantile(energy, cfg.coarse_trim_energy_q))
    act = np.where(energy > thr)[0]
    if len(act) == 0:
        return 0, len(energy)
    s = int(act[0])
    e = int(act[-1]) + 1
    min_len = int(max(2, round(cfg.coarse_trim_min_sec * fps)))
    if (e - s) < min_len:
        return 0, len(energy)
    return s, e


def _banded_dtw(x: np.ndarray, y: np.ndarray, qx: np.ndarray, qy: np.ndarray, band_ratio: float) -> AlignInfo:
    n, m = x.shape[0], y.shape[0]
    if n <= 0 or m <= 0:
        return AlignInfo(
            i_path=np.zeros(0, dtype=np.int32),
            j_path=np.zeros(0, dtype=np.int32),
            cost=1e18,
            path_length=0,
            warp_ratio=0.0,
            jump_rate=1.0,
        )

    def _solve_with_band(band: int) -> AlignInfo | None:
        inf = 1e18
        dp = np.full((n + 1, m + 1), inf, dtype=np.float64)
        prev = np.full((n + 1, m + 1), -1, dtype=np.int8)
        dp[0, 0] = 0.0

        for i in range(1, n + 1):
            j0 = max(1, i - band)
            j1 = min(m, i + band)
            xi = x[i - 1]
            for j in range(j0, j1 + 1):
                yj = y[j - 1]
                d = float(np.linalg.norm(xi - yj) / np.sqrt(x.shape[1]))
                q = float(max(0.05, min(1.0, 0.5 * (qx[i - 1] + qy[j - 1]))))
                # Do not discount low-quality frames to near-zero cost, otherwise
                # DTW can collapse to pathological paths. Low quality gets mild penalty.
                d *= (1.0 + 0.5 * (1.0 - q))

                a = dp[i - 1, j]
                b = dp[i, j - 1]
                c = dp[i - 1, j - 1]
                if c <= a and c <= b:
                    dp[i, j] = c + d
                    prev[i, j] = 2
                elif a <= b:
                    dp[i, j] = a + d
                    prev[i, j] = 0
                else:
                    dp[i, j] = b + d
                    prev[i, j] = 1

        if not np.isfinite(dp[n, m]):
            return None

        i, j = n, m
        ip, jp = [], []
        h_steps = 0
        while i > 0 and j > 0:
            ip.append(i - 1)
            jp.append(j - 1)
            p = int(prev[i, j])
            if p == 2:
                i -= 1
                j -= 1
            elif p == 0:
                i -= 1
                h_steps += 1
            else:
                j -= 1
                h_steps += 1

        ip.reverse()
        jp.reverse()
        ip_arr = np.asarray(ip, dtype=np.int32)
        jp_arr = np.asarray(jp, dtype=np.int32)
        plen = len(ip_arr)
        warp_ratio = float(plen / max(1, max(n, m)))
        jump_rate = float(h_steps / max(1, plen))

        return AlignInfo(
            i_path=ip_arr,
            j_path=jp_arr,
            cost=float(dp[n, m]),
            path_length=plen,
            warp_ratio=warp_ratio,
            jump_rate=jump_rate,
        )

    # First try user-configured band, then fallback to full band to avoid hard failure.
    band = int(max(abs(n - m), round(max(n, m) * band_ratio)))
    out = _solve_with_band(band)
    if out is not None:
        return out

    out = _solve_with_band(max(n, m))
    if out is not None:
        return out

    # Last-resort fallback: return a linear monotonic alignment path instead of
    # raising, so the pipeline can still produce report/timeline artifacts.
    i_path = np.arange(n, dtype=np.int32)
    if n <= 1 or m <= 1:
        j_path = np.zeros(n, dtype=np.int32)
    else:
        j_path = np.rint(np.linspace(0, m - 1, n)).astype(np.int32)
    j_path = np.clip(j_path, 0, max(0, m - 1))
    path_len = int(len(i_path))
    return AlignInfo(
        i_path=i_path,
        j_path=j_path,
        cost=1e18,
        path_length=path_len,
        warp_ratio=float(path_len / max(1, max(n, m))),
        jump_rate=1.0,
    )


def _build_map(i_path: np.ndarray, j_path: np.ndarray, Tt: int, fps_u: float, fps_t: float, cfg: PipelineConfig) -> tuple[np.ndarray, np.ndarray]:
    sums = np.zeros(Tt, dtype=np.float64)
    cnts = np.zeros(Tt, dtype=np.int32)
    for i, j in zip(i_path, j_path):
        sums[i] += float(j)
        cnts[i] += 1

    # Build anchor means on matched teacher frames, then interpolate through
    # unmatched frames. For head/tail outside anchor range, do linear
    # extrapolation instead of constant fill to avoid "flat then sudden jump".
    j_bar = np.zeros(Tt, dtype=np.float64)
    known = cnts > 0
    if np.any(known):
        ki = np.where(known)[0].astype(np.int32)
        kv = (sums[ki] / np.maximum(1, cnts[ki])).astype(np.float64)
        # Robustify anchors to be monotonic before interpolation.
        kv = np.maximum.accumulate(kv)
        all_i = np.arange(Tt, dtype=np.float64)
        j_bar = np.interp(all_i, ki.astype(np.float64), kv).astype(np.float64)

        # Linear extrapolation on both sides.
        if len(ki) >= 2:
            dki_l = max(1, int(ki[1] - ki[0]))
            dki_r = max(1, int(ki[-1] - ki[-2]))
            slope_l = float((kv[1] - kv[0]) / dki_l)
            slope_r = float((kv[-1] - kv[-2]) / dki_r)
            global_slope = float((kv[-1] - kv[0]) / max(1, int(ki[-1] - ki[0])))
        else:
            global_slope = float(fps_u / max(1e-6, fps_t))
            slope_l = global_slope
            slope_r = global_slope

        # Keep slopes physically plausible and monotonic.
        min_s = 0.05
        max_s = float(max(1.0, (fps_u / max(1e-6, fps_t)) * 2.5))
        slope_l = float(np.clip(slope_l, min_s, max_s))
        slope_r = float(np.clip(slope_r, min_s, max_s))
        global_slope = float(np.clip(global_slope, min_s, max_s))
        if not np.isfinite(slope_l):
            slope_l = global_slope
        if not np.isfinite(slope_r):
            slope_r = global_slope

        left = np.arange(0, int(ki[0]), dtype=np.float64)
        if len(left) > 0:
            j_bar[: int(ki[0])] = kv[0] + (left - float(ki[0])) * slope_l

        right = np.arange(int(ki[-1]) + 1, Tt, dtype=np.float64)
        if len(right) > 0:
            j_bar[int(ki[-1]) + 1 :] = kv[-1] + (right - float(ki[-1])) * slope_r
    else:
        j_bar[:] = 0.0

    win = int(max(5, round(cfg.map_smooth_win_sec * fps_t)))
    if win % 2 == 0:
        win += 1
    if Tt >= win:
        j_bar = savgol_filter(j_bar, window_length=win, polyorder=2)

    j_bar = np.maximum.accumulate(j_bar)
    # Limit local slope to avoid pathological tail jumps that can cause
    # unstable playback synchronization.
    max_inc = float(max(1.0, (fps_u / max(1e-6, fps_t)) * 2.5))
    dj = np.diff(j_bar, prepend=j_bar[0])
    dj = np.clip(dj, 0.0, max_inc)
    j_bar = j_bar[0] + np.cumsum(dj)

    j_max = float(np.max(j_path)) if len(j_path) > 0 else 0.0
    j_bar = np.clip(j_bar, 0.0, j_max)
    j_bar = np.maximum.accumulate(j_bar)

    # Fallback for pathological maps: if too many zero-increment steps, use a
    # globally linear monotonic map derived from alignment endpoints.
    if Tt >= 3:
        dj0 = np.diff(j_bar)
        zero_ratio = float(np.mean(dj0 <= 1e-6))
        if zero_ratio > 0.70 and len(i_path) >= 2 and len(j_path) >= 2:
            di = float(max(1, int(i_path[-1] - i_path[0])))
            slope = float((float(j_path[-1]) - float(j_path[0])) / di)
            slope = float(np.clip(slope, 0.05, max(1.0, (fps_u / max(1e-6, fps_t)) * 2.5)))
            ii = np.arange(Tt, dtype=np.float64)
            j_lin = float(j_path[0]) + (ii - float(i_path[0])) * slope
            j_lin = np.clip(j_lin, 0.0, j_max)
            j_bar = np.maximum.accumulate(j_lin)

    j_int = np.clip(np.rint(j_bar).astype(np.int32), 0, max(0, int(np.max(j_path))))
    map_user_sec = (j_bar / max(1e-6, fps_u)).astype(np.float32)
    return j_int, map_user_sec


def _aggregate_err(i_path: np.ndarray, per_pair_err: np.ndarray, Tt: int) -> np.ndarray:
    s = np.zeros(Tt, dtype=np.float64)
    c = np.zeros(Tt, dtype=np.int32)
    for i, e in zip(i_path, per_pair_err):
        s[i] += float(e)
        c[i] += 1
    out = np.full(Tt, np.nan, dtype=np.float64)
    good = c > 0
    out[good] = s[good] / c[good]
    return out


def _tempo(map_user_frame: np.ndarray, expected_ratio: float, fps_t: float, frame_quality: np.ndarray, cfg: PipelineConfig) -> tuple[np.ndarray, np.ndarray, list[dict], float]:
    j = np.maximum.accumulate(map_user_frame.astype(np.float64))
    w = int(max(2, round(cfg.tempo_win_sec * fps_t)))

    tr = np.zeros_like(j)
    for i in range(len(j)):
        i0 = max(0, i - w)
        i1 = min(len(j) - 1, i + w)
        di = max(1, i1 - i0)
        dj = j[i1] - j[i0]
        t_abs = dj / di
        tr[i] = t_abs / max(1e-6, expected_ratio)
    tr = np.clip(tr, 0.3, 3.0)

    conf = np.clip(frame_quality, 0.0, 1.0).astype(np.float32)

    min_len = int(max(1, round(cfg.tempo_min_dur_sec * fps_t)))
    segments = []

    def add_segs(mask: np.ndarray, typ: str):
        st = None
        for i, m in enumerate(mask):
            if m and st is None:
                st = i
            if (not m) and st is not None:
                ed = i - 1
                if (ed - st + 1) >= min_len:
                    seg = tr[st:ed + 1]
                    mean_abs = float(np.mean(np.abs(seg - 1.0)))
                    if mean_abs < 0.15:
                        sev = "mild"
                    elif mean_abs < 0.35:
                        sev = "clear"
                    else:
                        sev = "severe"
                    segments.append({
                        "type": typ,
                        "severity": sev,
                        "start_frame": int(st),
                        "end_frame": int(ed),
                        "start_sec": float(st / fps_t),
                        "end_sec": float(ed / fps_t),
                        "duration_sec": float((ed - st + 1) / fps_t),
                        "mean_tempo_rel": float(np.mean(seg)),
                    })
                st = None
        if st is not None:
            ed = len(mask) - 1
            if (ed - st + 1) >= min_len:
                seg = tr[st:ed + 1]
                mean_abs = float(np.mean(np.abs(seg - 1.0)))
                if mean_abs < 0.15:
                    sev = "mild"
                elif mean_abs < 0.35:
                    sev = "clear"
                else:
                    sev = "severe"
                segments.append({
                    "type": typ,
                    "severity": sev,
                    "start_frame": int(st),
                    "end_frame": int(ed),
                    "start_sec": float(st / fps_t),
                    "end_sec": float(ed / fps_t),
                    "duration_sec": float((ed - st + 1) / fps_t),
                    "mean_tempo_rel": float(np.mean(seg)),
                })

    valid = conf >= cfg.tempo_conf_quality_floor
    add_segs((tr > cfg.tempo_fast_thr) & valid, "fast")
    add_segs((tr < cfg.tempo_slow_thr) & valid, "slow")

    dev_area = float(np.mean(np.abs(tr - 1.0) * conf))
    return tr.astype(np.float32), conf.astype(np.float32), segments, dev_area


def _peak_pick(curve: np.ndarray, topk: int, min_gap: int, valid_mask: np.ndarray | None = None) -> list[int]:
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


def _score(mean_w_joint: float, tempo_dev_area: float, err_curve: np.ndarray, low_quality_ratio: float, cfg: PipelineConfig) -> ScoreBreakdown:
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
    total = float(np.clip(total, 0.0, 100.0))

    return ScoreBreakdown(pose, tempo, smooth, qpen, total)


def _joint_to_cn(name: str) -> str:
    return JOINT_CN.get(name, name)


def _advice_for_issue(issue_type: str, joint_name: str) -> str:
    jn = _joint_to_cn(joint_name)
    if issue_type == "tempo_fast":
        return f"该段节奏偏快，先把速度降下来，优先保证 {jn} 的轨迹清晰、到位再提速。"
    if issue_type == "tempo_slow":
        return f"该段节奏偏慢，建议提前准备发力点，重点提高 {jn} 的起落速度。"
    if issue_type == "tracking_bad":
        return "该段识别质量较差，建议正对镜头、增加光照并确保全身入镜后再练习。"
    return f"该段动作偏差较大，建议先分解练习 {jn}，再与上下肢连贯配合。"


def _build_beginner_report(
    frame_analysis: list[dict[str, Any]],
    tempo_segments: list[dict[str, Any]],
    top_joints: list[tuple[str, float]],
    score_total: float,
    fps_teacher: float,
) -> dict[str, Any]:
    if not frame_analysis:
        return {
            "summary": "当前未生成逐帧分析数据。",
            "issue_moments": [],
            "practice_focus": [],
        }

    n = len(frame_analysis)
    gap = int(max(1, round(0.6 * fps_teacher)))
    peak_frames: list[int] = []
    prev = -10**9
    for i, row in enumerate(frame_analysis):
        sev = str(row.get("severity", ""))
        fq = float(row.get("frame_quality", 1.0))
        tr = float(row.get("tempo_rel", 1.0))
        trigger = (sev in {"clear", "severe"}) or (fq < 0.45) or (tr > 1.15) or (tr < 0.85)
        if not trigger:
            continue
        if i - prev > gap:
            peak_frames.append(i)
        else:
            old = frame_analysis[peak_frames[-1]]
            old_err = float(old.get("frame_error") or 0.0)
            new_err = float(row.get("frame_error") or 0.0)
            if new_err >= old_err:
                peak_frames[-1] = i
        prev = i

    issue_moments: list[dict[str, Any]] = []
    for i in peak_frames[:12]:
        row = frame_analysis[i]
        sec = float(row.get("sec", i / max(1e-6, fps_teacher)))
        tr = float(row.get("tempo_rel", 1.0))
        fq = float(row.get("frame_quality", 1.0))
        top_rows = row.get("top_joints_at_frame") or []
        joint = str(top_rows[0].get("joint")) if top_rows else "left_shoulder"

        if fq < 0.40:
            issue_type = "tracking_bad"
            title = "跟踪质量偏低"
            reason = "该时刻人体关键点识别不稳定，动作判断可信度下降。"
        elif tr > 1.15:
            issue_type = "tempo_fast"
            title = "节奏偏快"
            reason = "该时刻动作推进快于教师示范，容易出现抢拍。"
        elif tr < 0.85:
            issue_type = "tempo_slow"
            title = "节奏偏慢"
            reason = "该时刻动作推进慢于教师示范，容易出现拖拍。"
        else:
            issue_type = "pose_error"
            title = "动作偏差较大"
            reason = f"该时刻 { _joint_to_cn(joint) } 的动作偏差较明显。"

        issue_moments.append(
            {
                "sec": sec,
                "frame": int(row.get("frame", i)),
                "title": title,
                "reason": reason,
                "joint_focus": _joint_to_cn(joint),
                "suggestion": _advice_for_issue(issue_type, joint),
                "severity": str(row.get("severity", "clear")),
            }
        )

    tempo_notes = []
    for seg in tempo_segments[:5]:
        typ = "偏快" if seg.get("type") == "fast" else "偏慢"
        tempo_notes.append(
            f"{float(seg.get('start_sec', 0.0)):.2f}s - {float(seg.get('end_sec', 0.0)):.2f}s：节奏{typ}"
        )

    focus = [_joint_to_cn(str(j[0])) for j in top_joints[:5]]
    if issue_moments:
        summary = (
            f"本次评分 {score_total:.1f} 分。共识别出 {len(issue_moments)} 个重点改进时刻，"
            "建议按时间顺序逐段练习。"
        )
    else:
        summary = f"本次评分 {score_total:.1f} 分。整体稳定，可重点精修细节与节奏一致性。"

    return {
        "summary": summary,
        "issue_moments": issue_moments,
        "tempo_notes": tempo_notes,
        "practice_focus": focus,
        "duration_sec": float((n - 1) / max(1e-6, fps_teacher)),
    }


def _joint_category(joint_name: str) -> str:
    if joint_name in {"left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"}:
        return "upper"
    if joint_name in {"left_hip", "right_hip"}:
        return "torso"
    if joint_name in {"left_knee", "right_knee", "left_ankle", "right_ankle", "left_foot_index", "right_foot_index"}:
        return "lower"
    return "upper"


def _teaching_drill(module_key: str, issue_type: str) -> str:
    if module_key == "tempo":
        return "跟拍练习：先用 0.75x 速度跟随示范 3 遍，再恢复原速，重点保持每拍起落一致。"
    if module_key == "upper":
        return "上肢分解：镜前慢练 8 次，关注肩-肘-腕的先后顺序与轨迹完整性。"
    if module_key == "torso":
        return "核心稳定：收紧核心后做 30 秒重心转换练习，避免躯干左右晃动。"
    if issue_type == "tracking_bad":
        return "识别优化：保证全身入镜并提高光照后再练，减少误判。"
    return "下肢节拍：跟节拍器做膝踝起落 16 拍，确保落点与示范一致。"


def _build_teaching_report(
    beginner_report: dict[str, Any],
    top_joints: list[tuple[str, float]],
    tempo_segments: list[dict[str, Any]],
    score_total: float,
) -> dict[str, Any]:
    issue_moments = list(beginner_report.get("issue_moments") or [])
    duration_sec = float(beginner_report.get("duration_sec") or 0.0)

    modules: dict[str, dict[str, Any]] = {
        "upper": {"title": "上肢控制", "goal": "提高手臂轨迹清晰度与到位时机。", "key_windows": [], "focus_joints": set()},
        "torso": {"title": "躯干稳定", "goal": "保持核心稳定，减少身体晃动。", "key_windows": [], "focus_joints": set()},
        "lower": {"title": "下肢与重心", "goal": "改善膝踝发力与重心转换。", "key_windows": [], "focus_joints": set()},
        "tempo": {"title": "节奏一致性", "goal": "让动作推进速度与示范保持一致。", "key_windows": [], "focus_joints": set()},
    }

    timeline_tasks: list[dict[str, Any]] = []

    for m in issue_moments:
        sec = float(m.get("sec", 0.0))
        start_sec = max(0.0, sec - 0.4)
        end_sec = min(duration_sec if duration_sec > 0 else sec + 0.4, sec + 0.4)
        title = str(m.get("title", "动作偏差"))
        reason = str(m.get("reason", ""))
        suggestion = str(m.get("suggestion", ""))
        joint_cn = str(m.get("joint_focus", ""))

        issue_type = "pose_error"
        if "节奏偏快" in title:
            issue_type = "tempo_fast"
        elif "节奏偏慢" in title:
            issue_type = "tempo_slow"
        elif "跟踪" in title:
            issue_type = "tracking_bad"

        if issue_type.startswith("tempo"):
            key = "tempo"
        else:
            joint_en = None
            for jn in LM_NAMES:
                if _joint_to_cn(jn) == joint_cn:
                    joint_en = jn
                    break
            key = _joint_category(joint_en or "left_shoulder")

        modules[key]["key_windows"].append(
            {
                "start_sec": round(start_sec, 2),
                "end_sec": round(end_sec, 2),
                "problem": title,
                "reason": reason,
                "suggestion": suggestion,
                "drill": _teaching_drill(key, issue_type),
            }
        )
        if joint_cn:
            modules[key]["focus_joints"].add(joint_cn)

        timeline_tasks.append(
            {
                "start_sec": round(start_sec, 2),
                "end_sec": round(end_sec, 2),
                "title": title,
                "what_happened": reason,
                "how_to_fix": suggestion,
            }
        )

    for seg in tempo_segments[:6]:
        modules["tempo"]["key_windows"].append(
            {
                "start_sec": round(float(seg.get("start_sec", 0.0)), 2),
                "end_sec": round(float(seg.get("end_sec", 0.0)), 2),
                "problem": "节奏片段偏差",
                "reason": "该片段速度与示范存在持续偏差。",
                "suggestion": "先降速分段练习，再回到原速保持稳定。",
                "drill": _teaching_drill("tempo", "tempo"),
            }
        )

    module_list = []
    for k in ["upper", "torso", "lower", "tempo"]:
        obj = modules[k]
        wins = obj["key_windows"][:6]
        module_list.append(
            {
                "module": obj["title"],
                "goal": obj["goal"],
                "focus_joints": sorted(list(obj["focus_joints"]))[:6],
                "key_windows": wins,
                "homework": [w["drill"] for w in wins[:2]] if wins else [_teaching_drill(k, "pose_error")],
            }
        )

    # A plain text report for direct reading/export.
    lines = [f"教学版动作改进报告（总分 {score_total:.1f}）"]
    for m in module_list:
        lines.append(f"【{m['module']}】目标：{m['goal']}")
        if m["focus_joints"]:
            lines.append(f"重点部位：{'、'.join(m['focus_joints'])}")
        for w in m["key_windows"][:3]:
            lines.append(
                f"- {w['start_sec']:.2f}s~{w['end_sec']:.2f}s：{w['problem']}；建议：{w['suggestion']}"
            )
        if m["homework"]:
            lines.append(f"课后练习：{m['homework'][0]}")

    return {
        "summary": "按上肢/躯干/下肢/节奏四个模块给出分段训练建议，适合初学者按时间点复练。",
        "modules": module_list,
        "timeline_tasks": timeline_tasks[:16],
        "text_report": "\n".join(lines),
    }


def _quality_snapshot(q: QualityInfo, cfg: PipelineConfig) -> dict[str, float]:
    frame_quality = np.clip(q.frame_quality.astype(np.float32), 0.0, 1.0)
    return {
        "mean_quality": float(np.mean(frame_quality)) if len(frame_quality) else 0.0,
        "invalid_ratio": float(np.mean(frame_quality < cfg.invalid_frame_quality_thr)) if len(frame_quality) else 1.0,
        "low_conf_ratio": float(np.mean(frame_quality < 0.55)) if len(frame_quality) else 1.0,
        "long_gap_ratio": float(len(q.long_gap_frames) / max(1, len(frame_quality))),
    }


def _build_confidence_summary(
    teacher_quality: QualityInfo,
    user_quality: QualityInfo,
    tempo_conf: np.ndarray,
    align: AlignInfo,
    *,
    bad_alignment: bool,
    cfg: PipelineConfig,
) -> dict[str, Any]:
    teacher = _quality_snapshot(teacher_quality, cfg)
    user = _quality_snapshot(user_quality, cfg)

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

    score = float(np.clip(
        0.5 * tracking_quality + 0.3 * alignment_stability + 0.2 * tempo_stability,
        0.0,
        1.0,
    ))

    if score >= 0.78:
        level = "high"
        summary = "?????????????????????????????"
    elif score >= 0.55:
        level = "medium"
        summary = "????????????????????????????"
    else:
        level = "low"
        summary = "????????????????????????????????????"

    issues: list[dict[str, Any]] = []
    if max(teacher["invalid_ratio"], user["invalid_ratio"]) >= 0.22:
        issues.append({
            "code": "tracking_coverage_low",
            "severity": "high" if max(teacher["invalid_ratio"], user["invalid_ratio"]) >= 0.35 else "medium",
            "message": "??????????????",
            "suggestion": "?????????????????????",
        })
    if max(teacher["long_gap_ratio"], user["long_gap_ratio"]) >= 0.10:
        issues.append({
            "code": "long_occlusion_gap",
            "severity": "medium",
            "message": "?????????????",
            "suggestion": "????????????????????",
        })
    if bad_alignment or align.jump_rate >= 0.35:
        issues.append({
            "code": "alignment_unstable",
            "severity": "high" if bad_alignment else "medium",
            "message": "???????????????????",
            "suggestion": "??????????????????????",
        })
    if tempo_stability < 0.60:
        issues.append({
            "code": "tempo_confidence_low",
            "severity": "medium",
            "message": "?????????????",
            "suggestion": "?????????????????????",
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


def _save_debug(out_dir: Path, i_path: np.ndarray, j_path: np.ndarray, err_curve: np.ndarray, markers: list[dict], tempo_rel: np.ndarray, tempo_segments: list[dict], frame_quality: np.ndarray) -> dict[str, str]:
    dbg = out_dir / "debug"
    ensure_dir(dbg)

    plt.figure(figsize=(6, 5))
    plt.plot(i_path, j_path, linewidth=1.0)
    plt.title("DTW alignment path")
    plt.xlabel("teacher frame")
    plt.ylabel("user frame")
    p1 = dbg / "align_path.png"
    plt.tight_layout()
    plt.savefig(p1, dpi=180)
    plt.close()

    plt.figure(figsize=(8, 3))
    plt.plot(err_curve, label="err_curve")
    for m in markers:
        if m["type"] == "pose_error":
            plt.axvline(m["frame"], color="r", alpha=0.4)
    plt.title("Error curve + pose markers")
    p2 = dbg / "err_curve_markers.png"
    plt.tight_layout()
    plt.savefig(p2, dpi=180)
    plt.close()

    plt.figure(figsize=(8, 3))
    plt.plot(tempo_rel, label="tempo_rel")
    plt.axhline(1.0, linestyle="--")
    for s in tempo_segments:
        c = "orange" if s["type"] == "fast" else "cyan"
        plt.axvspan(s["start_frame"], s["end_frame"], color=c, alpha=0.2)
    plt.title("Tempo rel + segments")
    p3 = dbg / "tempo_rel_segments.png"
    plt.tight_layout()
    plt.savefig(p3, dpi=180)
    plt.close()

    plt.figure(figsize=(8, 3))
    plt.plot(frame_quality, label="frame_quality")
    plt.ylim(0, 1)
    plt.title("Frame quality")
    p4 = dbg / "frame_quality_curve.png"
    plt.tight_layout()
    plt.savefig(p4, dpi=180)
    plt.close()

    return {
        "align_path": str(p1),
        "err_curve_markers": str(p2),
        "tempo_rel_segments": str(p3),
        "frame_quality_curve": str(p4),
    }


def run(
    root: Path,
    teacher_video_path: Path,
    user_video_path: Path,
    config: PipelineConfig | dict[str, Any] | None = None,
    result_id: str | None = None,
    pair_name: str | None = None,
) -> PipelineResult:
    cfg = PipelineConfig.from_obj(config)

    data_dir = root / "data"
    cache_dir = data_dir / "cache_keypoints"
    out_root = root / "outputs"
    ensure_dir(cache_dir)
    ensure_dir(out_root)

    teacher_stem = teacher_video_path.stem
    user_stem = user_video_path.stem
    pair = pair_name or f"{teacher_stem}_vs_{user_stem}"

    rid = result_id or make_result_id(pair)
    out_dir = out_root / pair
    ensure_dir(out_dir)

    t_world = cache_dir / f"standard__{teacher_stem}__world.npy"
    u_world = cache_dir / f"user__{user_stem}__world.npy"
    t_norm = cache_dir / f"standard__{teacher_stem}__norm.npy"
    u_norm = cache_dir / f"user__{user_stem}__norm.npy"
    t_meta = cache_dir / f"standard__{teacher_stem}__meta.json"
    u_meta = cache_dir / f"user__{user_stem}__meta.json"

    for p in [t_world, u_world, t_norm, u_norm, t_meta, u_meta]:
        if not p.exists():
            raise FileNotFoundError(f"Missing cache file: {p}")

    t_xyz_raw, t_vis = _load_arr(t_world)
    u_xyz_raw, u_vis = _load_arr(u_world)
    t_norm_raw = np.load(t_norm)
    u_norm_raw = np.load(u_norm)

    t_xyz, tq = _quality_and_fill(t_xyz_raw, t_vis, cfg)
    u_xyz, uq = _quality_and_fill(u_xyz_raw, u_vis, cfg)

    t_body = _normalize_body(t_xyz)
    u_body = _normalize_body(u_xyz)

    t_f, feat_dim = _build_feature(t_body, cfg)
    u_f, _ = _build_feature(u_body, cfg)

    # coarse trim
    t_fps = float(np.clip(float(__import__("json").loads(t_meta.read_text(encoding="utf-8")).get("fps_used", 30.0)), 1.0, 240.0))
    u_fps = float(np.clip(float(__import__("json").loads(u_meta.read_text(encoding="utf-8")).get("fps_used", 30.0)), 1.0, 240.0))

    ts, te = _trim_range(_motion_energy(t_body), t_fps, cfg)
    us, ue = _trim_range(_motion_energy(u_body), u_fps, cfg)

    t_f2 = t_f[ts:te]
    u_f2 = u_f[us:ue]
    tq2 = tq.frame_quality[ts:te]
    uq2 = uq.frame_quality[us:ue]

    # mirror check (user)
    base_align = _banded_dtw(t_f2, u_f2, tq2, uq2, cfg.dtw_band_ratio)
    base_cost = base_align.cost / max(1, base_align.path_length)

    u_body_m = _mirror_xyz(u_body)
    u_fm, _ = _build_feature(u_body_m, cfg)
    u_fm2 = u_fm[us:ue]
    mir_align = _banded_dtw(t_f2, u_fm2, tq2, uq2, cfg.dtw_band_ratio)
    mir_cost = mir_align.cost / max(1, mir_align.path_length)

    mirror_detected = False
    mirror_applied_to = None
    gain = 0.0

    if base_cost > 1e-9:
        gain = float((base_cost - mir_cost) / base_cost)
    if (mir_cost < base_cost) and (gain >= cfg.mirror_gain_force_apply):
        mirror_detected = True
        mirror_applied_to = "user"
        align = mir_align
        u_body_used = u_body_m
        u_f_used = u_fm
    else:
        align = base_align
        u_body_used = u_body
        u_f_used = u_f

    # global indices restored from trimmed alignment
    i_path = align.i_path + ts
    j_path = align.j_path + us

    # mapping
    teacher_to_user, map_user_sec = _build_map(i_path, j_path, Tt=t_body.shape[0], fps_u=u_fps, fps_t=t_fps, cfg=cfg)

    bad_alignment = (
        (not np.isfinite(align.cost))
        or (align.cost >= 1e17)
        or (align.jump_rate >= 0.90)
        or (float(np.mean(tq.frame_quality < cfg.invalid_frame_quality_thr)) >= 0.80)
    )
    if bad_alignment:
        # Fallback: keep synchronization stable even when DTW path is unreliable.
        Tt = t_body.shape[0]
        Tu = u_body_used.shape[0]
        if Tt > 1 and Tu > 1:
            teacher_to_user = np.rint(np.linspace(0, Tu - 1, Tt)).astype(np.int32)
        else:
            teacher_to_user = np.zeros(Tt, dtype=np.int32)
        teacher_to_user = np.clip(teacher_to_user, 0, max(0, Tu - 1))
        map_user_sec = (teacher_to_user.astype(np.float32) / max(1e-6, u_fps)).astype(np.float32)

    # weighted/unweighted path error
    diff_feat = np.linalg.norm(t_f[i_path] - u_f_used[j_path], axis=1) / np.sqrt(t_f.shape[1])
    path_q = np.minimum(tq.frame_quality[i_path], uq.frame_quality[j_path])
    weighted_feat_err = diff_feat * np.clip(path_q, 0.05, 1.0)

    err_curve = _aggregate_err(i_path, weighted_feat_err, t_f.shape[0]).astype(np.float32)

    # per-frame top joints + weighted joint error
    Tt = t_body.shape[0]
    per_frame_top_idx = np.zeros((Tt, 5), dtype=np.int16)
    per_frame_top_err = np.zeros((Tt, 5), dtype=np.float32)
    per_frame_top_conf = np.zeros((Tt, 5), dtype=np.float32)

    jw = []
    ju = []
    for i in range(Tt):
        j = int(np.clip(teacher_to_user[i], 0, u_body_used.shape[0] - 1))
        d = np.linalg.norm(t_body[i] - u_body_used[j], axis=1)
        conf = np.minimum(t_vis[i], u_vis[j])
        d = np.nan_to_num(d, nan=0.0, posinf=0.0, neginf=0.0)
        conf = np.nan_to_num(conf, nan=0.0, posinf=0.0, neginf=0.0)
        wd = d * np.clip(conf, 0.05, 1.0)
        jw.append(float(np.mean(wd)))
        ju.append(float(np.mean(d)))

        order = np.argsort(-d)[:5]
        per_frame_top_idx[i] = order.astype(np.int16)
        per_frame_top_err[i] = d[order].astype(np.float32)
        per_frame_top_conf[i] = conf[order].astype(np.float32)

    mean_w_joint = float(np.mean(jw))
    mean_u_joint = float(np.mean(ju))
    mean_feat = float(np.nanmean(err_curve))

    expected_ratio = float((ue - us) / max(1, (te - ts)))
    tempo_rel, tempo_conf, tempo_segments, tempo_dev_area = _tempo(
        map_user_frame=teacher_to_user.astype(np.float32),
        expected_ratio=expected_ratio,
        fps_t=t_fps,
        frame_quality=tq.frame_quality,
        cfg=cfg,
    )

    valid_pose = tq.frame_quality >= cfg.invalid_frame_quality_thr
    m_pose = _peak_pick(err_curve, cfg.marker_topk_pose, int(max(1, round(cfg.marker_min_gap_sec * t_fps))), valid_mask=valid_pose)

    m_tempo = []
    for s in tempo_segments[:cfg.marker_topk_tempo]:
        c = int(round((s["start_frame"] + s["end_frame"]) / 2))
        m_tempo.append(c)

    bad_mask = tq.frame_quality < cfg.invalid_frame_quality_thr
    bad_idx = np.where(bad_mask)[0]
    m_bad = []
    if len(bad_idx) > 0:
        step = max(1, len(bad_idx) // max(1, cfg.marker_topk_quality))
        m_bad = [int(bad_idx[k]) for k in range(0, len(bad_idx), step)][: cfg.marker_topk_quality]

    markers: list[dict[str, Any]] = []
    for f in m_pose:
        markers.append({"frame": int(f), "sec": float(f / t_fps), "type": "pose_error", "severity": "clear"})
    for f in m_tempo:
        markers.append({"frame": int(f), "sec": float(f / t_fps), "type": "tempo", "severity": "clear"})
    for f in m_bad:
        markers.append({"frame": int(f), "sec": float(f / t_fps), "type": "tracking_bad", "severity": "severe"})
    markers.sort(key=lambda x: x["frame"])

    # top joints global
    j_acc = np.zeros(33, dtype=np.float64)
    j_cnt = np.zeros(33, dtype=np.int32)
    for i in range(Tt):
        j = int(np.clip(teacher_to_user[i], 0, u_body_used.shape[0] - 1))
        d = np.linalg.norm(t_body[i] - u_body_used[j], axis=1)
        ok = np.isfinite(d)
        j_acc[ok] += d[ok]
        j_cnt[ok] += 1
    j_avg = np.divide(j_acc, np.maximum(1, j_cnt))
    order = np.argsort(-j_avg)[:8]
    top_joints = [(LM_NAMES[int(k)], float(j_avg[int(k)])) for k in order]

    score = _score(
        mean_w_joint=mean_w_joint,
        tempo_dev_area=tempo_dev_area,
        err_curve=err_curve,
        low_quality_ratio=float(np.mean(tq.frame_quality < 0.55)),
        cfg=cfg,
    )

    # per-frame explain rows
    frame_analysis = []
    for i in range(Tt):
        top_rows = []
        for k in range(5):
            idx = int(per_frame_top_idx[i, k])
            ev = float(per_frame_top_err[i, k])
            cf = float(per_frame_top_conf[i, k])
            top_rows.append({"joint": LM_NAMES[idx], "error": ev, "confidence": cf})

        tr = float(tempo_rel[i])
        if tr > cfg.tempo_fast_thr:
            tempo_text = "tempo_fast"
        elif tr < cfg.tempo_slow_thr:
            tempo_text = "tempo_slow"
        else:
            tempo_text = "tempo_ok"

        sev = "mild" if float(err_curve[i]) < mean_feat * 1.05 else ("clear" if float(err_curve[i]) < mean_feat * 1.35 else "severe")

        advice = f"Focus on {top_rows[0]['joint']}, severity={sev}, tempo={tempo_text}."
        frame_analysis.append({
            "frame": i,
            "sec": float(i / t_fps),
            "frame_error": float(err_curve[i]) if np.isfinite(err_curve[i]) else None,
            "frame_quality": float(tq.frame_quality[i]),
            "severity": sev,
            "tempo_rel": tr,
            "top_joints_at_frame": top_rows,
            "advice": advice,
        })

    # sync recommendation
    sync_reco = {
        "seek_threshold_sec": cfg.sync_seek_threshold_sec,
        "seek_cooldown_ms": cfg.sync_seek_cooldown_ms,
        "rate_min": cfg.sync_rate_min,
        "rate_max": cfg.sync_rate_max,
        "rate_gain": cfg.sync_rate_gain,
    }

    beginner_report = _build_beginner_report(
        frame_analysis=frame_analysis,
        tempo_segments=tempo_segments,
        top_joints=top_joints,
        score_total=score.total_score,
        fps_teacher=t_fps,
    )
    teaching_report = _build_teaching_report(
        beginner_report=beginner_report,
        top_joints=top_joints,
        tempo_segments=tempo_segments,
        score_total=score.total_score,
    )

    # marker arrays for npz
    marker_frames = np.asarray([m["frame"] for m in markers], dtype=np.int32)
    typ_map = {"pose_error": 0, "tempo": 1, "tracking_bad": 2}
    marker_types = np.asarray([typ_map.get(m["type"], 0) for m in markers], dtype=np.int8)
    sev_map = {"mild": 0, "clear": 1, "severe": 2}
    marker_sev = np.asarray([sev_map.get(m["severity"], 1) for m in markers], dtype=np.int8)

    quality_stats = {
        "teacher_mean_quality": float(np.mean(tq.frame_quality)) if len(tq.frame_quality) else 0.0,
        "teacher_invalid_ratio": float(np.mean(tq.frame_quality < cfg.invalid_frame_quality_thr)) if len(tq.frame_quality) else 1.0,
        "teacher_low_conf_ratio": float(np.mean(tq.frame_quality < 0.55)) if len(tq.frame_quality) else 1.0,
        "teacher_long_gap_ratio": float(len(tq.long_gap_frames) / max(1, len(tq.frame_quality))),
        "user_mean_quality": float(np.mean(uq.frame_quality)) if len(uq.frame_quality) else 0.0,
        "user_invalid_ratio": float(np.mean(uq.frame_quality < cfg.invalid_frame_quality_thr)) if len(uq.frame_quality) else 1.0,
        "user_low_conf_ratio": float(np.mean(uq.frame_quality < 0.55)) if len(uq.frame_quality) else 1.0,
        "user_long_gap_ratio": float(len(uq.long_gap_frames) / max(1, len(uq.frame_quality))),
    }
    confidence_summary = _build_confidence_summary(
        tq,
        uq,
        tempo_conf,
        align,
        bad_alignment=bad_alignment,
        cfg=cfg,
    )

    # report
    report = {
        "result_id": rid,
        "pair": f"{teacher_stem} vs {user_stem}",
        "pair_name": pair,
        "created_at": utc_ts(),
        "config": cfg.to_dict(),
        "input_meta": {
            "teacher_video": str(teacher_video_path),
            "user_video": str(user_video_path),
            "teacher_frames": int(t_body.shape[0]),
            "user_frames": int(u_body_used.shape[0]),
            "fps_teacher": float(t_fps),
            "fps_user": float(u_fps),
        },
        "quality_stats": quality_stats,
        "confidence": confidence_summary,
        "mirror_detected": bool(mirror_detected),
        "mirror_applied_to": mirror_applied_to,
        "mirror_gain": float(gain),
        "trimming": {
            "teacher_trim_frame": [int(ts), int(te)],
            "user_trim_frame": [int(us), int(ue)],
            "teacher_trim_sec": [float(ts / t_fps), float(te / t_fps)],
            "user_trim_sec": [float(us / u_fps), float(ue / u_fps)],
        },
        "feature": {
            "feature_type": cfg.feature_type_default,
            "dims": feat_dim,
        },
        "alignment_quality": {
            "path_length": int(align.path_length),
            "warp_ratio": float(align.warp_ratio),
            "jump_rate": float(align.jump_rate),
            "cost": float(align.cost),
            "fallback_linear_map_applied": bool(bad_alignment),
        },
        "scores": {
            "score_pose": score.score_pose,
            "score_tempo": score.score_tempo,
            "score_smooth": score.score_smooth,
            "score_quality_penalty": score.score_quality_penalty,
            "score_total": score.total_score,
        },
        "calibration": {
            "teacher_self_score": None,
            "user_self_score": None,
            "linear_calibration": {"scale": 1.0, "offset": 0.0},
            "applied": False,
        },
        "tempo": {
            "segments": tempo_segments,
            "deviation_area": tempo_dev_area,
        },
        "markers": markers,
        "recommendations": {
            "overall": "Keep stable torso and improve consistency on high-error joints.",
            "segments": [f"{s['type']} {s['start_sec']:.2f}-{s['end_sec']:.2f}s ({s['severity']})" for s in tempo_segments],
        },
        "beginner_report": beginner_report,
        "teaching_report": teaching_report,
        "sync_strategy_recommendation": sync_reco,
        "frame_analysis": frame_analysis,

        # legacy fields for compatibility
        "teacher_frames": int(t_body.shape[0]),
        "user_frames": int(u_body_used.shape[0]),
        "expected_ratio_user_per_teacher": expected_ratio,
        "mean_feature_error": mean_feat,
        "mean_joint_error_normcoords": mean_u_joint,
        "weighted_mean_joint_error": mean_w_joint,
        "unweighted_mean_joint_error": mean_u_joint,
        "score_0_100": score.total_score,
        "top_joints": top_joints,
        "fps_teacher": float(t_fps),
        "tempo_segments": tempo_segments,
    }

    dump_json(out_dir / "report.json", report)

    timeline_npz = out_dir / "timeline.npz"
    np.savez_compressed(
        timeline_npz,
        fps_teacher=np.float32(t_fps),
        fps_user=np.float32(u_fps),
        teacher_frames=np.int32(t_body.shape[0]),
        user_frames=np.int32(u_body_used.shape[0]),
        expected_ratio=np.float32(expected_ratio),
        teacher_to_user=teacher_to_user.astype(np.int32),
        map_user_sec=map_user_sec.astype(np.float32),
        err_curve=err_curve.astype(np.float32),
        tempo_rel=tempo_rel.astype(np.float32),
        tempo_rel_confidence=tempo_conf.astype(np.float32),
        frame_quality=tq.frame_quality.astype(np.float32),
        top_idx=per_frame_top_idx.astype(np.int16),
        top_err=per_frame_top_err.astype(np.float32),
        marker_frames=marker_frames,
        marker_types=marker_types,
        marker_severity=marker_sev,
        per_frame_joint_err_topk_idx=per_frame_top_idx.astype(np.int16),
        per_frame_joint_err_topk_val=per_frame_top_err.astype(np.float32),
        per_frame_joint_conf_topk=per_frame_top_conf.astype(np.float32),
    )

    timeline_json = {
        "pair": pair,
        "fps_teacher": float(t_fps),
        "fps_user": float(u_fps),
        "teacher_frames": int(t_body.shape[0]),
        "user_frames": int(u_body_used.shape[0]),
        "markers_sec": [float(f / t_fps) for f in marker_frames.tolist()],
    }
    dump_json(out_dir / "timeline.json", timeline_json)

    summary = {
        "result_id": rid,
        "pair_name": pair,
        "score_total": score.total_score,
        "score_pose": score.score_pose,
        "score_tempo": score.score_tempo,
        "score_smooth": score.score_smooth,
        "quality_low_conf_ratio": quality_stats["teacher_low_conf_ratio"],
        "mirror_detected": bool(mirror_detected),
        "feature_type": cfg.feature_type_default,
        "dtw_band_ratio": cfg.dtw_band_ratio,
        "confidence_score": confidence_summary["score"],
        "confidence_level": confidence_summary["level"],
        "confidence_summary": confidence_summary["summary"],
    }
    dump_json(out_dir / "summary.json", summary)

    calibration = {
        "method": "identity",
        "teacher_self_score": None,
        "user_self_score": None,
        "scale": 1.0,
        "offset": 0.0,
        "applied_to_total_score": False,
    }
    dump_json(out_dir / "calibration.json", calibration)

    dump_json(out_dir / "config.json", cfg.to_dict())

    if cfg.save_debug_plots:
        dbg = _save_debug(out_dir, i_path, j_path, err_curve, markers, tempo_rel, tempo_segments, tq.frame_quality)
        dump_json(out_dir / "debug_index.json", dbg)

    return PipelineResult(
        result_id=rid,
        pair_name=pair,
        out_dir=str(out_dir),
        report=report,
        timeline_npz=str(timeline_npz),
    )
