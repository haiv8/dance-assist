from __future__ import annotations

from fastapi import APIRouter

from app.schemas.dto import SystemActionResponse, SystemStatusResponse
from app.services.system_admin import cleanup_debug_artifacts, collect_system_status, rebuild_analysis_reports, trim_output_pairs

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
async def system_status_api():
    return SystemStatusResponse(**collect_system_status())


@router.post("/maintenance/rebuild-reports", response_model=SystemActionResponse)
async def rebuild_reports_api():
    return SystemActionResponse(**rebuild_analysis_reports())


@router.post("/maintenance/trim-outputs", response_model=SystemActionResponse)
async def trim_outputs_api(keep: int = 5):
    return SystemActionResponse(**trim_output_pairs(keep=keep))


@router.post("/maintenance/cleanup-debug", response_model=SystemActionResponse)
async def cleanup_debug_api():
    return SystemActionResponse(**cleanup_debug_artifacts())
