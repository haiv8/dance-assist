from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.dto import (
    RoleQueryType,
    RoleType,
    VideoActionResponse,
    VideoItem,
    VideoListResponse,
    VideoQualityPairRequest,
    VideoQualityResponse,
    VideoRenameRequest,
    VideoUploadResponse,
)
from app.services.storage import delete_video, list_videos, rename_video, save_upload
from app.services.video_quality import check_video_pair_quality, check_video_quality

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    role: RoleType = Form(...),
    name: str | None = Form(default=None),
):
    payload = await save_upload(file=file, role=role, name=name)
    return VideoUploadResponse(**payload)


@router.get("", response_model=VideoListResponse)
async def get_videos(role: RoleQueryType = "all"):
    items = list_videos(role=role)
    return VideoListResponse(items=items)


@router.get("/{video_id}/quality", response_model=VideoQualityResponse)
async def get_video_quality(video_id: str, role: RoleType | None = None):
    return VideoQualityResponse(**check_video_quality(video_id=video_id, role=role))


@router.post("/quality-check-pair", response_model=VideoQualityResponse)
async def check_video_quality_pair(payload: VideoQualityPairRequest):
    return VideoQualityResponse(
        **check_video_pair_quality(
            teacher_video_id=payload.teacher_video_id,
            user_video_id=payload.user_video_id,
        )
    )


@router.patch("/{video_id}", response_model=VideoActionResponse)
async def rename_video_api(video_id: str, payload: VideoRenameRequest, role: RoleType):
    item = rename_video(video_id=video_id, role=role, name=payload.name)
    return VideoActionResponse(
        ok=True,
        video_id=video_id,
        message="视频已重命名",
        item=VideoItem(**item),
    )


@router.delete("/{video_id}", response_model=VideoActionResponse)
async def delete_video_api(video_id: str, role: RoleType):
    delete_video(video_id=video_id, role=role)
    return VideoActionResponse(
        ok=True,
        video_id=video_id,
        message="视频已删除",
        item=None,
    )
