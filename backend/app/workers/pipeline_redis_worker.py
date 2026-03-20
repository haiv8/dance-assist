from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from app.services.pipeline import (
    _classify_pipeline_error,
    _pipeline_worker,
    _record_pipeline_event,
    _set_task,
)
from app.settings import settings

logger = logging.getLogger("dance_assist.pipeline_redis_worker")
PipelineWorker = Callable[..., bool]


def _redis_client():
    if not settings.REDIS_URL:
        raise RuntimeError("DANCE_ASSIST_REDIS_URL is required for redis pipeline worker")
    try:
        import redis
    except Exception as exc:
        raise RuntimeError(f"redis package unavailable: {exc}") from exc
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _max_attempts() -> int:
    return max(1, int(settings.PIPELINE_MAX_RETRIES) + 1)


def _normalized_attempt(payload: dict[str, Any]) -> int:
    try:
        return max(1, int(payload.get("attempt_count", 1)))
    except Exception:
        return 1


def _schedule_retry(client, payload: dict[str, Any], exc: Exception) -> bool:
    pipeline_id = str(payload.get("pipeline_id", "")).strip()
    current_attempt = _normalized_attempt(payload)
    max_attempts = _max_attempts()
    if (not pipeline_id) or current_attempt >= max_attempts:
        if pipeline_id:
            _record_pipeline_event(
                pipeline_id,
                "retry_exhausted",
                status="failed",
                message=f"retry exhausted after attempt {current_attempt}/{max_attempts}",
                executor="redis_queue",
                payload={
                    "attempt_count": current_attempt,
                    "max_attempts": max_attempts,
                    "error_type": _classify_pipeline_error(exc),
                },
            )
        return False

    next_attempt = current_attempt + 1
    error_type = _classify_pipeline_error(exc)
    _set_task(
        pipeline_id,
        {
            "status": "pending",
            "message": f"retry scheduled ({next_attempt}/{max_attempts})",
            "started_at": None,
            "finished_at": None,
            "executor": "redis_queue",
            "attempt_count": next_attempt,
            "retry_count": max(0, next_attempt - 1),
            "error_type": error_type,
        },
    )
    _record_pipeline_event(
        pipeline_id,
        "retry_scheduled",
        status="pending",
        message=f"retry scheduled ({next_attempt}/{max_attempts})",
        executor="redis_queue",
        payload={
            "attempt_count": current_attempt,
            "next_attempt_count": next_attempt,
            "max_attempts": max_attempts,
            "error_type": error_type,
        },
    )

    delay_sec = max(0, int(settings.PIPELINE_RETRY_BACKOFF_SEC)) * current_attempt
    if delay_sec > 0:
        time.sleep(delay_sec)

    retry_payload = {**payload, "attempt_count": next_attempt, "executor": "redis_queue"}
    client.rpush(settings.REDIS_PIPELINE_QUEUE, json.dumps(retry_payload, ensure_ascii=False))
    return True


def process_job_payload(client, payload: dict[str, Any], worker: PipelineWorker = _pipeline_worker) -> bool:
    pipeline_id = str(payload["pipeline_id"])
    attempt_count = _normalized_attempt(payload)
    try:
        return bool(
            worker(
                pipeline_id=pipeline_id,
                teacher_video_id=str(payload["teacher_video_id"]),
                user_video_id=str(payload["user_video_id"]),
                overwrite=bool(payload.get("overwrite", False)),
                raise_on_error=True,
                attempt_count=attempt_count,
                executor_backend="redis_queue",
            )
        )
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        logger.exception(
            "Redis pipeline worker failed to process job %s on attempt %s: %s",
            pipeline_id,
            attempt_count,
            exc,
        )
        return _schedule_retry(client, payload, exc)


def run_forever() -> int:
    client = _redis_client()
    queue_name = settings.REDIS_PIPELINE_QUEUE
    block_timeout = max(1, int(settings.REDIS_BLOCK_TIMEOUT_SEC))
    logger.info("Redis pipeline worker started for queue %s", queue_name)

    while True:
        item = client.blpop(queue_name, timeout=block_timeout)
        if not item:
            continue

        _, raw = item
        try:
            payload = json.loads(raw)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            logger.exception("Redis pipeline worker received invalid payload: %s", exc)
            time.sleep(1)
            continue

        process_job_payload(client, payload)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        return run_forever()
    except KeyboardInterrupt:
        logger.info("Redis pipeline worker stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
