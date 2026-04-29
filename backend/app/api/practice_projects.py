from __future__ import annotations

from fastapi import APIRouter

from app.schemas.dto import PracticeProjectDetailResponse, PracticeProjectListResponse
from app.services.practice_projects import get_practice_project, list_practice_projects

router = APIRouter(prefix="/practice-projects", tags=["practice-projects"])


@router.get("", response_model=PracticeProjectListResponse)
async def practice_projects_api(limit: int = 200):
    return PracticeProjectListResponse(**list_practice_projects(limit=limit))


@router.get("/{teacher_video_id}", response_model=PracticeProjectDetailResponse)
async def practice_project_detail_api(teacher_video_id: str, limit: int = 200):
    return PracticeProjectDetailResponse(**get_practice_project(teacher_video_id=teacher_video_id, limit=limit))
