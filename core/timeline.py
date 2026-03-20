from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from core.pipeline import run as run_pipeline


def generate_timeline(root: Path, teacher: str, user: str, marker_topk: int = 10) -> Path:
    """
    Compatibility wrapper:
    - Reuse outputs/<teacher>_vs_<user>/timeline.npz if exists
    - Otherwise run the upgraded pipeline to generate timeline/report/debug
    """
    out_dir = root / "outputs" / f"{teacher}_vs_{user}"
    timeline_npz = out_dir / "timeline.npz"
    if timeline_npz.exists():
        return timeline_npz

    teacher_video = root / "data" / "standard_videos" / f"{teacher}.mp4"
    user_video = root / "data" / "user_videos" / f"{user}.mp4"
    if not teacher_video.exists() or not user_video.exists():
        raise FileNotFoundError(
            f"Missing input videos: teacher={teacher_video.exists()} user={user_video.exists()}"
        )

    run_pipeline(
        root=root,
        teacher_video_path=teacher_video,
        user_video_path=user_video,
        config={"marker_topk_pose": int(marker_topk)},
        pair_name=f"{teacher}_vs_{user}",
    )

    if not timeline_npz.exists():
        raise RuntimeError(f"Pipeline did not produce timeline.npz: {timeline_npz}")

    timeline_json = out_dir / "timeline.json"
    if not timeline_json.exists():
        tl = np.load(timeline_npz)
        fps_teacher = float(tl["fps_teacher"])
        marker_frames = tl["marker_frames"].astype(np.int32)
        timeline_json.write_text(
            json.dumps(
                {
                    "pair": f"{teacher} vs {user}",
                    "fps_teacher": fps_teacher,
                    "fps_user": float(tl["fps_user"]),
                    "teacher_frames": int(tl["teacher_frames"]),
                    "user_frames": int(tl["user_frames"]),
                    "expected_ratio": float(tl["expected_ratio"]) if "expected_ratio" in tl.files else None,
                    "markers_sec": [float(m / max(1e-6, fps_teacher)) for m in marker_frames.tolist()],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding='utf-8',
        )

    return timeline_npz
