from __future__ import annotations

from fastapi import APIRouter

from app.schemas.dto import RecordWorkspaceResponse
from app.services.records import list_records_workspace

router = APIRouter(prefix="/records", tags=["records"])


@router.get("/workspace", response_model=RecordWorkspaceResponse)
async def records_workspace_api(limit: int = 100):
    return RecordWorkspaceResponse(**list_records_workspace(limit=limit))
