from __future__ import annotations

import json
import logging
import os
import socket
import time
from datetime import datetime, timezone
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _job_timeout_sec(payload: dict[str, Any]) -> int | None:
    raw = payload.get("timeout_sec", settings.PIPELINE_JOB_TIMEOUT_SEC)
    try:
        value = int(raw or 0)
    except Exception:
        return None
    return value if value > 0 else None


def _heartbeat_key() -> str:
    return str(settings.REDIS_WORKER_HEARTBEAT_KEY).strip() or f"{settings.REDIS_PIPELINE_QUEUE}:worker_heartbeat"


def _heartbeat_ttl_sec() -> int:
    try:
        ttl = int(settings.REDIS_WORKER_HEARTBEAT_TTL_SEC)
    except Exception:
        ttl = 30
    return max(10, ttl)


def _dead_letter_queue_name() -> str:
    configured = str(settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE).strip()
    return configured or f"{settings.REDIS_PIPELINE_QUEUE}:dead_letter"


def _write_worker_heartbeat(
    client,
    *,
    state: str,
    pipeline_id: str | None = None,
    attempt_count: int | None = None,
    detail: str | None = None,
) -> None:
    payload = {
        "updated_at": _utc_now(),
        "state": state,
        "pipeline_id": pipeline_id,
        "attempt_count": attempt_count,
        "detail": detail,
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "queue": settings.REDIS_PIPELINE_QUEUE,
    }
    try:
        client.set(_heartbeat_key(), json.dumps(payload, ensure_ascii=False), ex=_heartbeat_ttl_sec())
    except Exception:
        logger.debug("Failed to write worker heartbeat", exc_info=True)


def _push_dead_letter(
    client,
    *,
    reason: str,
    payload: dict[str, Any] | None = None,
    raw_payload: str | None = None,
    exc: Exception | None = None,
    detail: str | None = None,
) -> None:
    record = {
        "reason": reason,
        "queue": settings.REDIS_PIPELINE_QUEUE,
        "failed_at": _utc_now(),
        "payload": payload,
        "raw_payload": raw_payload,
        "detail": detail,
        "error_type": _classify_pipeline_error(exc) if exc is not None else None,
        "error": f"{type(exc).__name__}: {exc}" if exc is not None else None,
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
    }
    try:
        client.rpush(_dead_letter_queue_name(), json.dumps(record, ensure_ascii=False))
    except Exception:
        logger.exception("Failed to push payload into dead letter queue")


def _schedule_retry(client, payload: dict[str, Any], exc: Exception) -> bool:
    pipeline_id = str(payload.get("pipeline_id", "")).strip()
    current_attempt = _normalized_attempt(payload)
    max_attempts = _max_attempts()
    error_type = _classify_pipeline_error(exc)

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
                    "error_type": error_type,
                    "timeout_sec": _job_timeout_sec(payload),
                },
            )
        _push_dead_letter(
            client,
            reason="retry_exhausted" if pipeline_id else "missing_pipeline_id",
            payload=payload,
            exc=exc,
            detail=f"attempt {current_attempt}/{max_attempts} exhausted",
        )
        return False

    next_attempt = current_attempt + 1
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
            "timeout_sec": _job_timeout_sec(payload),
        },
    )

    delay_sec = max(0, int(settings.PIPELINE_RETRY_BACKOFF_SEC)) * current_attempt
    if delay_sec > 0:
        _write_worker_heartbeat(
            client,
            state="retry_backoff",
            pipeline_id=pipeline_id,
            attempt_count=current_attempt,
            detail=f"sleeping {delay_sec}s before retry",
        )
        time.sleep(delay_sec)

    retry_payload = {**payload, "attempt_count": next_attempt, "executor": "redis_queue", "timeout_sec": _job_timeout_sec(payload)}
    client.rpush(settings.REDIS_PIPELINE_QUEUE, json.dumps(retry_payload, ensure_ascii=False))
    return True


def process_job_payload(client, payload: dict[str, Any], worker: PipelineWorker = _pipeline_worker) -> bool:
    pipeline_id = str(payload.get("pipeline_id", "")).strip()
    attempt_count = _normalized_attempt(payload)
    timeout_sec = _job_timeout_sec(payload)
    _write_worker_heartbeat(
        client,
        state="processing",
        pipeline_id=pipeline_id or None,
        attempt_count=attempt_count,
        detail=f"timeout={timeout_sec or 0}s",
    )
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
                timeout_sec=timeout_sec,
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
    finally:
        _write_worker_heartbeat(client, state="idle")


def run_forever() -> int:
    client = _redis_client()
    queue_name = settings.REDIS_PIPELINE_QUEUE
    block_timeout = max(1, int(settings.REDIS_BLOCK_TIMEOUT_SEC))
    logger.info("Redis pipeline worker started for queue %s", queue_name)
    _write_worker_heartbeat(client, state="idle", detail="worker booted")

    while True:
        _write_worker_heartbeat(client, state="idle")
        item = client.blpop(queue_name, timeout=block_timeout)
        if not item:
            continue

        _, raw = item
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("job payload must be an object")
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            logger.exception("Redis pipeline worker received invalid payload: %s", exc)
            _push_dead_letter(client, reason="invalid_payload", raw_payload=raw, exc=exc)
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
