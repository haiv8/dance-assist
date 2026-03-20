# core/pose_mediapipe.py
# MediaPipe 0.10.30+ 已移除 mp.solutions，因此这里用 MediaPipe Tasks 的 PoseLandmarker

import os
import json
import urllib.request
from pathlib import Path
from typing import Optional, List, Tuple

import cv2
import numpy as np
import mediapipe as mp

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

# 官方模型（Full / Lite），脚本会自动下载到 ./models/
MODEL_URL_LITE = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
MODEL_URL_FULL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)

# BlazePose 33点骨架连接（来自官方仓库 pose_connections.py）
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


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def list_videos(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS])


def download_if_needed(model_path: Path, prefer_full: bool = True) -> Path:
    """
    若模型不存在则自动下载。
    prefer_full=True -> 下载 full 模型；否则下载 lite 模型。
    """
    ensure_dir(model_path.parent)
    if model_path.exists() and model_path.stat().st_size > 1024 * 1024:
        return model_path

    url = MODEL_URL_FULL if prefer_full else MODEL_URL_LITE
    print(f"[MODEL] Downloading model from:\n  {url}\n  -> {model_path}")
    try:
        urllib.request.urlretrieve(url, str(model_path))
    except Exception as e:
        raise RuntimeError(
            f"模型下载失败：{e}\n"
            f"你可以手动下载（Pose Landmarker 模型页面）并放到：{model_path}"
        )
    return model_path


def get_video_info(cap: cv2.VideoCapture) -> dict:
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    return {"fps": fps, "width": w, "height": h, "frame_count": n}


def draw_landmarks_on_bgr(frame_bgr: np.ndarray, landmarks_norm: List, color=(0, 255, 0)) -> np.ndarray:
    """简单画点 + 画骨架线（normalized -> pixel）"""
    h, w = frame_bgr.shape[:2]
    out = frame_bgr.copy()

    # 画线
    for a, b in POSE_CONNECTIONS:
        if a >= len(landmarks_norm) or b >= len(landmarks_norm):
            continue
        la, lb = landmarks_norm[a], landmarks_norm[b]
        if la is None or lb is None:
            continue
        xa, ya = int(la.x * w), int(la.y * h)
        xb, yb = int(lb.x * w), int(lb.y * h)
        cv2.line(out, (xa, ya), (xb, yb), color, 2)

    # 画点
    for lm in landmarks_norm:
        if lm is None:
            continue
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(out, (x, y), 3, (0, 0, 255), -1)

    return out


def extract_pose_landmarker_video(
    video_path: Path,
    model_path: Path,
    out_norm_npy: Path,
    out_world_npy: Path,
    out_meta_json: Path,
    out_overlay_video: Optional[Path] = None,
    max_frames: int = 0,
    num_poses: int = 1,
    min_pose_det_conf: float = 0.5,
    min_pose_presence_conf: float = 0.5,
    min_tracking_conf: float = 0.5,
) -> Tuple[Path, Path, Path, Optional[Path]]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    meta = get_video_info(cap)
    fps = meta["fps"] if meta["fps"] and meta["fps"] > 1e-6 else 30.0
    meta["fps_used"] = fps

    # 可选输出叠加视频
    writer = None
    if out_overlay_video is not None:
        ensure_dir(out_overlay_video.parent)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_overlay_video), fourcc, fps, (meta["width"], meta["height"]))
        if not writer.isOpened():
            cap.release()
            raise RuntimeError(f"Cannot open VideoWriter: {out_overlay_video}")

    # 构建 PoseLandmarker（VIDEO 模式）
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=num_poses,
        min_pose_detection_confidence=min_pose_det_conf,
        min_pose_presence_confidence=min_pose_presence_conf,
        min_tracking_confidence=min_tracking_conf,
    )

    norm_seq = []
    world_seq = []

    with PoseLandmarker.create_from_options(options) as landmarker:
        frame_idx = 0
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break

            if max_frames and frame_idx >= max_frames:
                break

            # timestamp 必须单调递增（ms）
            timestamp_ms = int(frame_idx * 1000.0 / fps)
            frame_idx += 1

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if not result.pose_landmarks:
                norm_arr = np.full((33, 4), np.nan, dtype=np.float32)
                world_arr = np.full((33, 4), np.nan, dtype=np.float32)
                norm_seq.append(norm_arr)
                world_seq.append(world_arr)
                if writer is not None:
                    writer.write(frame_bgr)
                continue

            # 取第一个人（通常就 1 个）
            norm_lms = result.pose_landmarks[0]
            world_lms = result.pose_world_landmarks[0] if result.pose_world_landmarks else None

            # normalized
            norm_arr = np.zeros((33, 4), dtype=np.float32)
            for i, lm in enumerate(norm_lms):
                vis = getattr(lm, "visibility", np.nan)
                norm_arr[i] = (lm.x, lm.y, lm.z, float(vis) if vis is not None else np.nan)

            # world
            if world_lms is None:
                world_arr = np.full((33, 4), np.nan, dtype=np.float32)
            else:
                world_arr = np.zeros((33, 4), dtype=np.float32)
                for i, lm in enumerate(world_lms):
                    vis = getattr(lm, "visibility", np.nan)
                    world_arr[i] = (lm.x, lm.y, lm.z, float(vis) if vis is not None else np.nan)

            norm_seq.append(norm_arr)
            world_seq.append(world_arr)

            if writer is not None:
                overlay = draw_landmarks_on_bgr(frame_bgr, norm_lms)
                writer.write(overlay)

    cap.release()
    if writer is not None:
        writer.release()

    if len(norm_seq) == 0:
        raise RuntimeError(f"No frames read from: {video_path}")

    norm_kp = np.stack(norm_seq, axis=0)   # [T,33,4]
    world_kp = np.stack(world_seq, axis=0) # [T,33,4]

    ensure_dir(out_norm_npy.parent)
    np.save(out_norm_npy, norm_kp)
    np.save(out_world_npy, world_kp)

    meta["read_frames"] = int(norm_kp.shape[0])
    meta["norm_shape"] = list(norm_kp.shape)
    meta["world_shape"] = list(world_kp.shape)
    meta["source_video"] = str(video_path)

    ensure_dir(out_meta_json.parent)
    with open(out_meta_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[OK] {video_path.name}")
    print(f"     -> {out_norm_npy}   shape={norm_kp.shape}")
    print(f"     -> {out_world_npy}  shape={world_kp.shape}")
    print(f"     -> {out_meta_json}")
    if out_overlay_video is not None:
        print(f"     -> {out_overlay_video}")

    return out_norm_npy, out_world_npy, out_meta_json, out_overlay_video


def batch_extract(
    standard_dir: Path,
    user_dir: Path,
    cache_dir: Path,
    model_path: Path,
    write_overlay: bool = False,
    overlay_dir: Optional[Path] = None,
    max_frames: int = 0,
):
    ensure_dir(cache_dir)
    if write_overlay:
        overlay_dir = overlay_dir or (cache_dir.parent / "outputs" / "overlay_videos")
        ensure_dir(overlay_dir)

    videos = []
    videos += [(p, "standard") for p in list_videos(standard_dir)]
    videos += [(p, "user") for p in list_videos(user_dir)]

    if not videos:
        print("No videos found. Please put videos into:")
        print(f"  {standard_dir}")
        print(f"  {user_dir}")
        return

    # 每个视频单独创建 landmarker（最稳，timestamp 不会跨视频冲突）
    for video_path, tag in videos:
        stem = video_path.stem
        out_norm = cache_dir / f"{tag}__{stem}__norm.npy"
        out_world = cache_dir / f"{tag}__{stem}__world.npy"
        out_meta = cache_dir / f"{tag}__{stem}__meta.json"

        out_overlay = None
        if write_overlay and overlay_dir is not None:
            out_overlay = overlay_dir / f"{tag}__{stem}__overlay.mp4"

        extract_pose_landmarker_video(
            video_path=video_path,
            model_path=model_path,
            out_norm_npy=out_norm,
            out_world_npy=out_world,
            out_meta_json=out_meta,
            out_overlay_video=out_overlay,
            max_frames=max_frames,
        )


if __name__ == "__main__":
    # 项目根目录（脚本在 core/ 下）
    root = Path(__file__).resolve().parents[1]

    standard_dir = root / "data" / "standard_videos"
    user_dir = root / "data" / "user_videos"
    cache_dir = root / "data" / "cache_keypoints"

    model_dir = root / "models"
    model_path = model_dir / "pose_landmarker_full.task"  # 默认 full
    model_path = download_if_needed(model_path, prefer_full=True)

    batch_extract(
        standard_dir=standard_dir,
        user_dir=user_dir,
        cache_dir=cache_dir,
        model_path=model_path,
        write_overlay=False,  # 想生成叠加视频改 True
        max_frames=0,         # 测试可先改 300
    )