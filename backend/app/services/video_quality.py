from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException

from app.services.storage import RoleType, get_video_meta


QualityLevel = Literal["good", "warning", "error"]


def _level_rank(level: str) -> int:
    return {"good": 0, "warning": 1, "error": 2}.get(level, 0)


def _max_level(levels: list[QualityLevel]) -> QualityLevel:
    if not levels:
        return "good"
    return max(levels, key=_level_rank)


def _check(key: str, label: str, level: QualityLevel, message: str, value: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "key": key,
        "label": label,
        "level": level,
        "message": message,
    }
    if value is not None:
        payload["value"] = value
    return payload


def _parse_fps(raw: Any) -> float | None:
    text = str(raw or "").strip()
    if not text or text == "0/0":
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            den = float(right)
            if abs(den) < 1e-9:
                return None
            return float(left) / den
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _run_ffprobe(path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe executable not found") from exc
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid json") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("ffprobe returned invalid payload")
    return payload


def _extract_video_probe(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    streams = payload.get("streams")
    video_stream = None
    if isinstance(streams, list):
        for stream in streams:
            if isinstance(stream, dict) and stream.get("codec_type") == "video":
                video_stream = stream
                break
    fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    return video_stream, fmt


def _inspect_video(video_id: str, role: RoleType | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    try:
        stored = get_video_meta(video_id, role)
    except HTTPException as exc:
        return None, [
            _check(
                "exists",
                "视频文件",
                "error",
                f"没有找到视频：{video_id}",
                {"video_id": video_id, "status_code": exc.status_code},
            )
        ]

    path = Path(str(stored.get("path") or ""))
    if not path.exists():
        return None, [
            _check("exists", "视频文件", "error", "视频记录存在，但本地文件缺失", {"video_id": video_id, "path": str(path)})
        ]

    checks.append(_check("exists", "视频文件", "good", "视频文件存在", {"video_id": video_id}))

    meta: dict[str, Any] = {
        "video_id": stored.get("video_id"),
        "role": stored.get("role"),
        "filename": stored.get("filename"),
        "size_bytes": int(stored.get("size_bytes") or path.stat().st_size),
        "duration_sec": None,
        "width": None,
        "height": None,
        "fps": None,
        "readable": False,
    }

    try:
        payload = _run_ffprobe(path)
        stream, fmt = _extract_video_probe(payload)
        if stream is None:
            raise RuntimeError("no video stream found")
        duration = stream.get("duration") or fmt.get("duration")
        width = stream.get("width")
        height = stream.get("height")
        fps = _parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
        size = fmt.get("size")
        meta.update(
            {
                "duration_sec": float(duration) if duration not in (None, "") else None,
                "width": int(width) if width not in (None, "") else None,
                "height": int(height) if height not in (None, "") else None,
                "fps": fps,
                "size_bytes": int(size) if size not in (None, "") else meta["size_bytes"],
                "readable": True,
            }
        )
        checks.append(_check("readable", "元信息读取", "good", "ffprobe 可以读取视频元信息"))
    except Exception as exc:
        meta["error"] = str(exc)
        checks.append(_check("readable", "元信息读取", "error", f"无法读取视频元信息：{exc}"))
        return meta, checks

    duration_value = float(meta["duration_sec"] or 0)
    if duration_value < 5:
        checks.append(_check("duration", "视频时长", "warning", "视频过短，建议使用 5 秒以上的完整动作片段", duration_value))
    else:
        checks.append(_check("duration", "视频时长", "good", "视频时长满足基础分析要求", duration_value))

    width = int(meta["width"] or 0)
    height = int(meta["height"] or 0)
    if width < 480 or height < 360:
        checks.append(_check("resolution", "分辨率", "warning", "分辨率偏低，可能影响姿态识别稳定性", {"width": width, "height": height}))
    else:
        checks.append(_check("resolution", "分辨率", "good", "分辨率满足基础分析要求", {"width": width, "height": height}))

    fps = float(meta["fps"] or 0)
    if fps < 15:
        checks.append(_check("fps", "帧率", "warning", "帧率偏低，快动作可能不够连续", round(fps, 2)))
    else:
        checks.append(_check("fps", "帧率", "good", "帧率满足基础分析要求", round(fps, 2)))

    checks.append(_check("size", "文件大小", "good", "已读取文件大小", int(meta["size_bytes"] or 0)))
    return meta, checks


def _recommendations_for(level: QualityLevel, checks: list[dict[str, Any]]) -> list[str]:
    if level == "good":
        return ["视频基础质量满足分析要求，可以继续发起分析。"]
    recommendations: list[str] = []
    keys = {str(item.get("key") or "") for item in checks if item.get("level") in {"warning", "error"}}
    if "readable" in keys or "exists" in keys:
        recommendations.append("请重新上传可正常播放的视频后再分析。")
    if "duration" in keys:
        recommendations.append("建议保留完整动作片段，开始和结束各预留 1-2 秒缓冲。")
    if "resolution" in keys:
        recommendations.append("建议固定机位、全身入镜，并使用至少 480x360 的视频。")
    if "fps" in keys:
        recommendations.append("建议使用 15 fps 以上的视频，快动作尽量使用 25-30 fps。")
    if "duration_ratio" in keys:
        recommendations.append("两段视频时长差异较大时仍可分析，但评分更需要结合回放和可信度理解。")
    return recommendations or ["当前视频存在质量风险，建议结合视频回看理解评分结果。"]


def _summary_for(level: QualityLevel) -> str:
    if level == "good":
        return "视频质量检查通过，可以继续发起分析。"
    if level == "warning":
        return "视频可以继续分析，但存在可能影响评分或可信度的风险。"
    return "视频无法正常读取，建议更换或重新上传后再分析。"


def check_video_quality(video_id: str, role: RoleType | None = None) -> dict[str, Any]:
    meta, checks = _inspect_video(video_id, role)
    level = _max_level([str(item.get("level") or "good") for item in checks])  # type: ignore[arg-type]
    return {
        "ok": level != "error",
        "level": level,
        "summary": _summary_for(level),
        "checks": checks,
        "teacher_meta": meta if meta and meta.get("role") == "teacher" else None,
        "user_meta": meta if meta and meta.get("role") == "user" else None,
        "recommendations": _recommendations_for(level, checks),
    }


def check_video_pair_quality(teacher_video_id: str, user_video_id: str) -> dict[str, Any]:
    teacher_meta, teacher_checks = _inspect_video(teacher_video_id, "teacher")
    user_meta, user_checks = _inspect_video(user_video_id, "user")
    checks = teacher_checks + user_checks

    teacher_duration = float((teacher_meta or {}).get("duration_sec") or 0)
    user_duration = float((user_meta or {}).get("duration_sec") or 0)
    if teacher_duration > 0 and user_duration > 0:
        ratio = teacher_duration / user_duration
        value = {
            "teacher_duration_sec": round(teacher_duration, 3),
            "user_duration_sec": round(user_duration, 3),
            "ratio": round(ratio, 3),
            "diff_sec": round(abs(teacher_duration - user_duration), 3),
        }
        if ratio > 1.5 or ratio < 0.67:
            checks.append(_check("duration_ratio", "时长差异", "warning", "教师和学员视频时长差异较大", value))
        else:
            checks.append(_check("duration_ratio", "时长差异", "good", "两段视频时长差异在可接受范围内", value))

    level = _max_level([str(item.get("level") or "good") for item in checks])  # type: ignore[arg-type]
    return {
        "ok": level != "error",
        "level": level,
        "summary": _summary_for(level),
        "checks": checks,
        "teacher_meta": teacher_meta,
        "user_meta": user_meta,
        "recommendations": _recommendations_for(level, checks),
    }
