# core/render_overlay.py
from __future__ import annotations

from pathlib import Path
import subprocess

import cv2
import numpy as np

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26),
    (25, 27), (26, 28),
    (27, 29), (28, 30),
    (29, 31), (30, 32),
    (27, 31), (28, 32),
]


def _ffmpeg_to_h264(src_video: Path, audio_from: Path, dst: Path, fps: float) -> None:
    """Convert to browser-friendly H.264 + yuv420p and keep source audio when present."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-i", str(src_video),
        "-i", str(audio_from),
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-r", str(max(1.0, float(fps))),
        "-vsync", "cfr",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-g", "30",
        "-keyint_min", "30",
        "-sc_threshold", "0",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg transcode failed:\n{r.stderr}\ncmd: {' '.join(cmd)}")


def render_overlay_video_h264(
    video_path: Path,
    norm_npy: Path,
    out_mp4_h264: Path,
    vis_thresh: float = 0.2,
    hold_max_gap: int = 8,
    max_height: int = 720,
    overwrite: bool = False,
) -> Path:
    """
    Draw skeleton overlay from norm.npy, write temp mp4v, then transcode to H.264.

    hold_max_gap: for missing frames, keep last reliable joint positions up to N frames.
    This avoids one-frame empty skeleton when detection briefly drops.
    """
    out_mp4_h264.parent.mkdir(parents=True, exist_ok=True)
    if out_mp4_h264.exists() and (not overwrite):
        return out_mp4_h264

    kp = np.load(norm_npy)  # [T, 33, 4]
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if w <= 0 or h <= 0:
        cap.release()
        raise RuntimeError("Invalid video size.")

    if h > max_height:
        new_h = max_height
        new_w = int(w * new_h / h)
        if new_w % 2 == 1:
            new_w += 1
    else:
        new_w, new_h = w, h

    tmp = out_mp4_h264.with_suffix(".tmp.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp), fourcc, fps, (new_w, new_h))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Cannot open VideoWriter: {tmp}")

    t_frames = kp.shape[0]
    last_xy = np.full((33, 2), np.nan, dtype=np.float32)
    last_seen = np.full(33, -10**9, dtype=np.int32)

    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        if idx >= t_frames:
            break

        if (new_w, new_h) != (w, h):
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        h2, w2 = frame.shape[:2]
        arr = kp[idx]  # [33, 4]
        xs, ys, vs = arr[:, 0], arr[:, 1], arr[:, 3]

        valid_now = (
            np.isfinite(xs)
            & np.isfinite(ys)
            & np.isfinite(vs)
            & (vs >= vis_thresh)
        )

        draw_xy = np.full((33, 2), np.nan, dtype=np.float32)
        for j in range(33):
            if bool(valid_now[j]):
                xj = float(np.clip(xs[j] * w2, 0, w2 - 1))
                yj = float(np.clip(ys[j] * h2, 0, h2 - 1))
                draw_xy[j, 0] = xj
                draw_xy[j, 1] = yj
                last_xy[j, 0] = xj
                last_xy[j, 1] = yj
                last_seen[j] = idx
                continue

            if (idx - int(last_seen[j])) <= int(max(0, hold_max_gap)):
                if np.isfinite(last_xy[j, 0]) and np.isfinite(last_xy[j, 1]):
                    draw_xy[j, 0] = last_xy[j, 0]
                    draw_xy[j, 1] = last_xy[j, 1]

        for a, b in POSE_CONNECTIONS:
            xa, ya = draw_xy[a]
            xb, yb = draw_xy[b]
            if (not np.isfinite(xa)) or (not np.isfinite(ya)) or (not np.isfinite(xb)) or (not np.isfinite(yb)):
                continue
            cv2.line(frame, (int(xa), int(ya)), (int(xb), int(yb)), (0, 255, 0), 2)

        for j in range(33):
            x = draw_xy[j, 0]
            y = draw_xy[j, 1]
            if (not np.isfinite(x)) or (not np.isfinite(y)):
                continue
            cv2.circle(frame, (int(x), int(y)), 3, (0, 0, 255), -1)

        writer.write(frame)
        idx += 1

    cap.release()
    writer.release()

    _ffmpeg_to_h264(tmp, video_path, out_mp4_h264, fps=fps)

    try:
        tmp.unlink()
    except Exception:
        pass

    return out_mp4_h264
