from __future__ import annotations

from fastapi import APIRouter

from app.schemas.dto import AiCoachRequest, AiCoachResponse, AiProviderStatusResponse
from app.services.ai_coach import ai_provider_status, generate_ai_coach
from app.services.pipeline import get_pipeline_result_summary

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/reports/{pipeline_id}/coach", response_model=AiCoachResponse)
async def ai_report_coach_api(pipeline_id: str, body: AiCoachRequest | None = None):
    _ = body
    summary = get_pipeline_result_summary(pipeline_id)
    return AiCoachResponse(**generate_ai_coach(summary))


@router.get("/status", response_model=AiProviderStatusResponse)
async def ai_status_api():
    return AiProviderStatusResponse(**ai_provider_status())
