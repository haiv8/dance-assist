from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Response

from app.schemas.dto import RecordFlagsPatchRequest, RecordFlagsResponse, RecordWorkspaceResponse
from app.services.record_export import build_records_csv
from app.services.record_flags import load_record_flags, update_record_flags
from app.services.records import list_records_workspace

router = APIRouter(prefix="/records", tags=["records"])


@router.get("/workspace", response_model=RecordWorkspaceResponse)
async def records_workspace_api(limit: int = 50):
    return RecordWorkspaceResponse(**list_records_workspace(limit=limit))


@router.get("/flags")
async def record_flags_api():
    return {"items": load_record_flags()}


@router.get("/export.csv")
async def export_records_csv_api(limit: int = 200, starred: bool | None = None, status: str | None = None):
    allowed_status = {"done", "failed", "running"}
    normalized_status = str(status).strip() if status is not None else None
    if normalized_status not in allowed_status:
        normalized_status = None
    content = build_records_csv(limit=limit, starred=starred, status=normalized_status)
    filename = f"dance_assist_records_{date.today().isoformat()}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{pipeline_id}/flags", response_model=RecordFlagsResponse)
async def patch_record_flags_api(pipeline_id: str, payload: RecordFlagsPatchRequest):
    return RecordFlagsResponse(**update_record_flags(pipeline_id, starred=payload.starred, note=payload.note))
