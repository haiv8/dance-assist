from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException


@dataclass
class PipelineFailure(Exception):
    error_type: str
    error_message: str
    error_suggestion: str
    raw_error: str = ""

    def __str__(self) -> str:
        return self.raw_error or self.error_message


ERROR_DEFINITIONS: dict[str, tuple[str, str]] = {
    "video_missing": ("视频文件不存在", "请回到素材库确认教师/学员视频仍在本地，必要时重新上传后再分析。"),
    "video_unreadable": ("视频无法读取", "请确认视频可以正常播放，或转为常见 MP4/H.264 格式后重新上传。"),
    "ffmpeg_missing": ("缺少 ffmpeg 或 ffprobe", "请安装 ffmpeg，并确认 ffmpeg、ffprobe 已加入系统 PATH，重启桌面程序后再试。"),
    "pose_cache_missing": ("姿态缓存缺失或损坏", "请使用覆盖历史结果重新分析，系统会重新提取姿态缓存。"),
    "model_missing": ("姿态模型缺失或不可用", "请确认 pose_landmarker_full.task 已放入 models 目录，或重新执行模型准备步骤。"),
    "low_quality_input": ("输入视频质量严重不足", "请检查视频是否可读、全身入镜、光照和遮挡情况，必要时重新拍摄或重新上传。"),
    "pipeline_internal_error": ("分析内部异常", "请保留原始视频和任务 ID，查看后端日志中的 raw_error 进一步定位。"),
    "canceled": ("任务已取消", "如果需要结果，请重新发起分析任务。"),
    "timeout": ("分析任务超时", "建议缩短视频时长，或检查后台 Worker/硬件负载后重试。"),
}


def _definition(error_type: str) -> tuple[str, str]:
    return ERROR_DEFINITIONS.get(error_type, ERROR_DEFINITIONS["pipeline_internal_error"])


def build_failure_payload(
    error_type: str,
    *,
    raw_error: str | None = None,
    message: str | None = None,
    suggestion: str | None = None,
) -> dict[str, str]:
    default_message, default_suggestion = _definition(error_type)
    return {
        "error_type": error_type,
        "error_message": message or default_message,
        "error_suggestion": suggestion or default_suggestion,
        "raw_error": raw_error or "",
    }


def input_quality_failure(input_quality: dict[str, Any]) -> PipelineFailure:
    checks = input_quality.get("checks") if isinstance(input_quality.get("checks"), list) else []
    failing_keys = {str(item.get("key") or "") for item in checks if isinstance(item, dict) and item.get("level") == "error"}
    raw_error = str(input_quality.get("summary") or "input quality check failed")

    if any("ffprobe" in str(item.get("message") or "").lower() for item in checks if isinstance(item, dict)):
        payload = build_failure_payload("ffmpeg_missing", raw_error=raw_error)
    elif "exists" in failing_keys:
        payload = build_failure_payload("video_missing", raw_error=raw_error)
    elif "readable" in failing_keys:
        payload = build_failure_payload("video_unreadable", raw_error=raw_error)
    else:
        payload = build_failure_payload("low_quality_input", raw_error=raw_error)
    return PipelineFailure(**payload)


def map_pipeline_exception(exc: Exception) -> dict[str, str]:
    if isinstance(exc, PipelineFailure):
        return build_failure_payload(
            exc.error_type,
            raw_error=exc.raw_error or str(exc),
            message=exc.error_message,
            suggestion=exc.error_suggestion,
        )

    raw_error = f"{type(exc).__name__}: {exc}"
    raw_lower = raw_error.lower()

    if isinstance(exc, HTTPException):
        if exc.status_code == 404:
            return build_failure_payload("video_missing", raw_error=raw_error)
        return build_failure_payload("pipeline_internal_error", raw_error=raw_error)

    if isinstance(exc, FileNotFoundError):
        filename = str(getattr(exc, "filename", "") or "")
        if "ffmpeg" in filename.lower() or "ffprobe" in filename.lower() or "ffmpeg" in raw_lower or "ffprobe" in raw_lower:
            return build_failure_payload("ffmpeg_missing", raw_error=raw_error)
        if "pose_landmarker" in raw_lower or ".task" in raw_lower or "model" in raw_lower:
            return build_failure_payload("model_missing", raw_error=raw_error)
        return build_failure_payload("video_missing", raw_error=raw_error)

    if isinstance(exc, subprocess.SubprocessError) or "ffmpeg" in raw_lower or "ffprobe" in raw_lower:
        return build_failure_payload("ffmpeg_missing", raw_error=raw_error)

    if "cannot open video" in raw_lower or "no frames read" in raw_lower or "video" in raw_lower and "read" in raw_lower:
        return build_failure_payload("video_unreadable", raw_error=raw_error)

    if "pose_landmarker" in raw_lower or ".task" in raw_lower or "model" in raw_lower:
        return build_failure_payload("model_missing", raw_error=raw_error)

    if "cache_keypoints" in raw_lower or "norm.npy" in raw_lower or "world.npy" in raw_lower:
        return build_failure_payload("pose_cache_missing", raw_error=raw_error)

    if isinstance(exc, TimeoutError):
        return build_failure_payload("timeout", raw_error=raw_error)

    return build_failure_payload("pipeline_internal_error", raw_error=raw_error)
