from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from typing import Any

from app.settings import settings

logger = logging.getLogger("dance_assist.pipeline_executor")
PipelineWorker = Callable[..., Any]


def _job_timeout_sec() -> int | None:
    try:
        timeout_sec = int(settings.PIPELINE_JOB_TIMEOUT_SEC)
    except Exception:
        return None
    return timeout_sec if timeout_sec > 0 else None


class PipelineExecutor:
    backend_name = "unknown"

    def submit(
        self,
        worker: PipelineWorker,
        pipeline_id: str,
        teacher_video_id: str,
        user_video_id: str,
        overwrite: bool,
    ) -> Any:
        raise NotImplementedError


class LocalThreadPipelineExecutor(PipelineExecutor):
    backend_name = "local_thread"

    def submit(
        self,
        worker: PipelineWorker,
        pipeline_id: str,
        teacher_video_id: str,
        user_video_id: str,
        overwrite: bool,
    ) -> threading.Thread:
        thread = threading.Thread(
            target=worker,
            args=(pipeline_id, teacher_video_id, user_video_id, overwrite),
            kwargs={"timeout_sec": _job_timeout_sec()},
            daemon=True,
            name=f"pipeline-{pipeline_id}",
        )
        thread.start()
        return thread


class RedisQueuePipelineExecutor(PipelineExecutor):
    backend_name = "redis_queue"

    def submit(
        self,
        worker: PipelineWorker,
        pipeline_id: str,
        teacher_video_id: str,
        user_video_id: str,
        overwrite: bool,
    ) -> dict[str, Any]:
        client = self._client()
        payload = {
            "pipeline_id": pipeline_id,
            "teacher_video_id": teacher_video_id,
            "user_video_id": user_video_id,
            "overwrite": overwrite,
            "executor": self.backend_name,
            "attempt_count": 1,
            "timeout_sec": _job_timeout_sec(),
        }
        client.rpush(settings.REDIS_PIPELINE_QUEUE, json.dumps(payload, ensure_ascii=False))
        return payload

    def _client(self):
        if not settings.REDIS_URL:
            raise RuntimeError("DANCE_ASSIST_REDIS_URL is required for redis_queue executor")
        try:
            import redis
        except Exception as exc:
            raise RuntimeError(f"redis package unavailable: {exc}") from exc
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


_EXECUTORS: dict[str, PipelineExecutor] = {
    "local_thread": LocalThreadPipelineExecutor(),
    "redis_queue": RedisQueuePipelineExecutor(),
}


def get_pipeline_executor() -> PipelineExecutor:
    configured = (settings.PIPELINE_EXECUTOR or "local_thread").strip().lower()
    executor = _EXECUTORS.get(configured)
    if executor is not None:
        return executor

    logger.warning(
        "Unknown pipeline executor '%s'; falling back to local_thread",
        settings.PIPELINE_EXECUTOR,
    )
    return _EXECUTORS["local_thread"]


def get_pipeline_executor_backend() -> str:
    return get_pipeline_executor().backend_name


def submit_pipeline_job(
    worker: PipelineWorker,
    pipeline_id: str,
    teacher_video_id: str,
    user_video_id: str,
    overwrite: bool,
) -> Any:
    executor = get_pipeline_executor()
    return executor.submit(worker, pipeline_id, teacher_video_id, user_video_id, overwrite)
