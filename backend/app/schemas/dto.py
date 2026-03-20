from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RoleType = Literal["teacher", "user"]
RoleQueryType = Literal["teacher", "user", "all"]
PipelineStatusType = Literal["pending", "running", "done", "failed", "canceled"]


class VideoUploadResponse(BaseModel):
    video_id: str
    role: RoleType
    filename: str
    size_bytes: int
    url: str
    meta_url: str


class VideoItem(BaseModel):
    video_id: str
    role: RoleType
    filename: str
    url: str
    uploaded_at: datetime
    size_bytes: int


class VideoListResponse(BaseModel):
    items: list[VideoItem]


class VideoRenameRequest(BaseModel):
    name: str


class VideoActionResponse(BaseModel):
    ok: bool
    video_id: str
    message: str
    item: VideoItem | None = None


class PipelineRunRequest(BaseModel):
    teacher_video_id: str
    user_video_id: str
    overwrite: bool = False


class PipelineRunResponse(BaseModel):
    pipeline_id: str
    pair_name: str
    status: PipelineStatusType
    queued_at: str | None = None
    updated_at: str | None = None
    executor: str | None = None
    attempt_count: int | None = None
    retry_count: int | None = None
    error_type: str | None = None
    stage: str | None = None
    progress: float | None = None
    cancel_requested: bool = False
    cancel_requested_at: str | None = None


class PipelineStatusResponse(BaseModel):
    pipeline_id: str
    pair_name: str
    status: PipelineStatusType
    message: str | None = None
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None
    executor: str | None = None
    attempt_count: int | None = None
    retry_count: int | None = None
    error_type: str | None = None
    stage: str | None = None
    progress: float | None = None
    cancel_requested: bool = False
    cancel_requested_at: str | None = None


class PipelineResultResponse(BaseModel):
    pipeline_id: str
    pair_name: str
    status: PipelineStatusType
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None
    executor: str | None = None
    attempt_count: int | None = None
    retry_count: int | None = None
    error_type: str | None = None
    stage: str | None = None
    progress: float | None = None
    cancel_requested: bool = False
    cancel_requested_at: str | None = None
    report: dict | None = None
    timeline: dict | None = None
    files: dict | None = None


class PipelineResultSummaryResponse(BaseModel):
    pipeline_id: str
    pair_name: str
    status: PipelineStatusType
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None
    executor: str | None = None
    attempt_count: int | None = None
    retry_count: int | None = None
    error_type: str | None = None
    stage: str | None = None
    progress: float | None = None
    cancel_requested: bool = False
    cancel_requested_at: str | None = None
    report: dict | None = None
    timeline: dict | None = None
    files: dict | None = None


class PipelineFrameDetailResponse(BaseModel):
    pipeline_id: str
    pair_name: str
    status: PipelineStatusType
    frame: int
    frame_analysis: dict | None = None


class PipelineFrameRangeItem(BaseModel):
    frame: int
    sec: float | None = None
    frame_analysis: dict | None = None


class PipelineFrameRangeResponse(BaseModel):
    pipeline_id: str
    pair_name: str
    status: PipelineStatusType
    start_frame: int
    end_frame: int
    total: int
    fps_teacher: float | None = None
    items: list[PipelineFrameRangeItem]


class PipelineTaskItem(BaseModel):
    pipeline_id: str
    pair_name: str
    status: PipelineStatusType
    stage: str | None = None
    progress: float | None = None
    teacher_video_id: str | None = None
    user_video_id: str | None = None
    executor: str | None = None
    attempt_count: int | None = None
    retry_count: int | None = None
    error_type: str | None = None
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None
    score_total: float | None = None
    confidence_score: float | None = None
    cancel_requested: bool = False
    cancel_requested_at: str | None = None


class PipelineTaskListResponse(BaseModel):
    items: list[PipelineTaskItem]
    total: int
    status_filter: str | None = None
    limit: int


class AnalysisReportItem(BaseModel):
    pipeline_id: str
    pair_name: str | None = None
    teacher_video_id: str | None = None
    user_video_id: str | None = None
    status: PipelineStatusType
    stage: str | None = None
    executor: str | None = None
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None
    score_total: float | None = None
    score_pose: float | None = None
    score_tempo: float | None = None
    confidence_score: float | None = None
    confidence_level: str | None = None
    overall_advice: str | None = None
    confidence_summary: str | None = None
    beginner_summary: str | None = None
    teaching_summary: str | None = None
    top_joints: list = Field(default_factory=list)
    files: dict | None = None


class AnalysisReportListResponse(BaseModel):
    items: list[AnalysisReportItem]
    total: int
    limit: int
    query: str | None = None
    min_score: float | None = None
    min_confidence: float | None = None


class AnalysisReportDetailResponse(AnalysisReportItem):
    report: dict | None = None


class FailureStatItem(BaseModel):
    key: str
    count: int


class PipelineFailureEventItem(BaseModel):
    pipeline_id: str
    event_type: str
    status: str | None = None
    executor: str | None = None
    error_type: str | None = None
    message: str | None = None
    created_at: datetime | None = None


class PipelineFailureStatsResponse(BaseModel):
    window_days: int
    total_failures: int
    by_error_type: list[FailureStatItem]
    by_executor: list[FailureStatItem]
    recent_failures: list[PipelineFailureEventItem]


class SystemStorageEntry(BaseModel):
    path: str
    bytes: int
    megabytes: float


class SystemStatusResponse(BaseModel):
    ok: bool
    checked_at: str | None = None
    task_store: str | None = None
    pipeline_executor: str | None = None
    app_home: str | None = None
    retain_output_pairs: int | None = None
    output_pair_count: int | None = None
    checks: dict
    paths: dict
    storage: dict[str, SystemStorageEntry]


class SystemActionResponse(BaseModel):
    ok: bool
    action: str
    message: str
    report_count: int | None = None
    affected_count: int | None = None
    freed_bytes: int | None = None


