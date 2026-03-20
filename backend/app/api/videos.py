from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.dto import (
    RoleQueryType,
    RoleType,
    VideoActionResponse,
    VideoItem,
    VideoListResponse,
    VideoRenameRequest,
    VideoUploadResponse,
)
from app.services.storage import delete_video, list_videos, rename_video, save_upload

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


@router.patch("/{video_id}", response_model=VideoActionResponse)
async def rename_video_api(video_id: str, payload: VideoRenameRequest, role: RoleType):
    item = rename_video(video_id=video_id, role=role, name=payload.name)
    return VideoActionResponse(
        ok=True,
        video_id=video_id,
        message="???????",
        item=VideoItem(**item),
    )


@router.delete("/{video_id}", response_model=VideoActionResponse)
async def delete_video_api(video_id: str, role: RoleType):
    deleted = delete_video(video_id=video_id, role=role)
    return VideoActionResponse(
        ok=True,
        video_id=video_id,
        message="?????",
        item=None,
    )
