from __future__ import annotations

from fastapi import APIRouter

from app.schemas.dto import (
    PipelineFailureStatsResponse,
    PipelineFrameDetailResponse,
    PipelineFrameRangeResponse,
    PipelineResultResponse,
    PipelineResultSummaryResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineStatusResponse,
    PipelineTaskListResponse,
)
from app.services.pipeline import (
    get_pipeline_failure_stats,
    get_pipeline_frame_detail,
    get_pipeline_frame_range,
    get_pipeline_result,
    get_pipeline_result_summary,
    get_pipeline_status,
    list_pipeline_tasks,
    request_pipeline_cancel,
    run_pipeline,
)

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("", response_model=PipelineTaskListResponse)
async def pipeline_tasks_api(limit: int = 50, status: str | None = None):
    return PipelineTaskListResponse(**list_pipeline_tasks(limit=limit, status=status))


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline_api(body: PipelineRunRequest):
    task = run_pipeline(
        teacher_video_id=body.teacher_video_id,
        user_video_id=body.user_video_id,
        overwrite=body.overwrite,
    )
    return PipelineRunResponse(**get_pipeline_status(task.get("pipeline_id", "")))


@router.get("/stats/failures", response_model=PipelineFailureStatsResponse)
async def pipeline_failure_stats_api(days: int = 30, limit: int = 20):
    return PipelineFailureStatsResponse(**get_pipeline_failure_stats(days=days, limit=limit))


@router.get("/{pipeline_id}/status", response_model=PipelineStatusResponse)
async def pipeline_status_api(pipeline_id: str):
    return PipelineStatusResponse(**get_pipeline_status(pipeline_id))


@router.post("/{pipeline_id}/cancel", response_model=PipelineStatusResponse)
async def pipeline_cancel_api(pipeline_id: str):
    return PipelineStatusResponse(**request_pipeline_cancel(pipeline_id))


@router.get("/{pipeline_id}/result", response_model=PipelineResultResponse)
async def pipeline_result_api(pipeline_id: str):
    return PipelineResultResponse(**get_pipeline_result(pipeline_id))


@router.get("/{pipeline_id}/result/summary", response_model=PipelineResultSummaryResponse)
async def pipeline_result_summary_api(pipeline_id: str):
    return PipelineResultSummaryResponse(**get_pipeline_result_summary(pipeline_id))


@router.get("/{pipeline_id}/result/frame/{frame}", response_model=PipelineFrameDetailResponse)
async def pipeline_frame_detail_api(pipeline_id: str, frame: int):
    return PipelineFrameDetailResponse(**get_pipeline_frame_detail(pipeline_id, frame))


@router.get("/{pipeline_id}/result/frames", response_model=PipelineFrameRangeResponse)
async def pipeline_frame_range_api(
    pipeline_id: str,
    start_frame: int | None = None,
    end_frame: int | None = None,
    start_sec: float | None = None,
    end_sec: float | None = None,
):
    return PipelineFrameRangeResponse(
        **get_pipeline_frame_range(
            pipeline_id,
            start_frame=start_frame,
            end_frame=end_frame,
            start_sec=start_sec,
            end_sec=end_sec,
        )
    )
