from __future__ import annotations

from fastapi import APIRouter

from app.schemas.dto import AnalysisReportDetailResponse, AnalysisReportListResponse
from app.services.pipeline import get_analysis_report, list_analysis_reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=AnalysisReportListResponse)
async def analysis_reports_api(
    limit: int = 50,
    q: str | None = None,
    min_score: float | None = None,
    min_confidence: float | None = None,
):
    return AnalysisReportListResponse(
        **list_analysis_reports(
            limit=limit,
            query=q,
            min_score=min_score,
            min_confidence=min_confidence,
        )
    )


@router.get("/{pipeline_id}", response_model=AnalysisReportDetailResponse)
async def analysis_report_detail_api(pipeline_id: str):
    return AnalysisReportDetailResponse(**get_analysis_report(pipeline_id))
