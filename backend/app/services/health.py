from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.task_store import task_store
from app.settings import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_app_home() -> dict[str, Any]:
    path = settings.APP_HOME
    writable = False
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / '.__health_probe__'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink(missing_ok=True)
        writable = True
    except Exception as exc:
        return {
            'status': 'fail',
            'ok': False,
            'path': str(path),
            'detail': f'{type(exc).__name__}: {exc}',
        }

    return {
        'status': 'pass',
        'ok': True,
        'path': str(path),
        'writable': writable,
        'detail': f'app home ready ({path})',
    }


def _check_disk() -> dict[str, Any]:
    usage = shutil.disk_usage(settings.APP_HOME)
    total_gb = round(usage.total / (1024 ** 3), 2)
    free_gb = round(usage.free / (1024 ** 3), 2)
    used_gb = round(usage.used / (1024 ** 3), 2)
    used_percent = round((usage.used / usage.total) * 100, 2) if usage.total else 0.0
    ok = free_gb >= float(settings.MIN_FREE_DISK_GB)
    return {
        'status': 'pass' if ok else 'fail',
        'ok': ok,
        'path': str(settings.APP_HOME),
        'total_gb': total_gb,
        'used_gb': used_gb,
        'free_gb': free_gb,
        'used_percent': used_percent,
        'min_free_gb': settings.MIN_FREE_DISK_GB,
        'detail': f'free {free_gb} GB / total {total_gb} GB',
    }


def _check_model_file() -> dict[str, Any]:
    runtime_model = settings.MODELS_DIR / 'pose_landmarker_full.task'
    legacy_model = settings.LEGACY_MODELS_DIR / 'pose_landmarker_full.task'
    path = runtime_model if runtime_model.exists() else legacy_model
    exists = path.exists()
    size_bytes = path.stat().st_size if exists else 0
    return {
        'status': 'pass' if exists else 'fail',
        'ok': exists,
        'path': str(path),
        'runtime_path': str(runtime_model),
        'legacy_path': str(legacy_model),
        'size_bytes': size_bytes,
        'detail': f'model ready ({round(size_bytes / (1024 ** 2), 2)} MB)' if exists else 'pose model file is missing',
    }


def _check_postgresql() -> dict[str, Any]:
    enabled = bool(settings.DATABASE_URL)
    required = enabled
    if not enabled:
        return {
            'status': 'disabled',
            'ok': True,
            'enabled': False,
            'required': required,
            'backend': task_store.backend_name,
            'detail': 'database disabled',
        }

    try:
        task_store.initialize()
        with task_store._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT current_database(), current_user')
                row = cur.fetchone()
        return {
            'status': 'pass',
            'ok': True,
            'enabled': True,
            'required': required,
            'backend': task_store.backend_name,
            'database': row[0] if row else None,
            'user': row[1] if row else None,
            'detail': f'connected to {row[0]} as {row[1]}' if row else 'database connection ok',
        }
    except Exception as exc:
        return {
            'status': 'fail',
            'ok': False,
            'enabled': True,
            'required': required,
            'backend': task_store.backend_name,
            'detail': f'{type(exc).__name__}: {exc}',
        }


def _parse_heartbeat(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _check_redis() -> dict[str, Any]:
    enabled = bool(settings.REDIS_URL)
    required = settings.PIPELINE_EXECUTOR == 'redis_queue'
    if not enabled:
        return {
            'status': 'disabled',
            'ok': not required,
            'enabled': False,
            'required': required,
            'queue': settings.REDIS_PIPELINE_QUEUE,
            'dead_letter_queue': settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE,
            'detail': 'redis disabled',
        }

    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = bool(client.ping())
        pending_jobs = int(client.llen(settings.REDIS_PIPELINE_QUEUE))
        dead_letter_jobs = int(client.llen(settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE))
        heartbeat = _parse_heartbeat(client.get(settings.REDIS_WORKER_HEARTBEAT_KEY))
        heartbeat_updated_at = heartbeat.get('updated_at')
        heartbeat_age_sec: float | None = None
        worker_alive: bool | None = None
        if isinstance(heartbeat_updated_at, str) and heartbeat_updated_at:
            try:
                heartbeat_dt = datetime.fromisoformat(heartbeat_updated_at.replace('Z', '+00:00'))
                heartbeat_age_sec = max(0.0, (datetime.now(timezone.utc) - heartbeat_dt.astimezone(timezone.utc)).total_seconds())
                worker_alive = heartbeat_age_sec <= max(10, int(settings.REDIS_WORKER_HEARTBEAT_TTL_SEC) * 1.5)
            except Exception:
                heartbeat_age_sec = None
                worker_alive = False if required else None
        elif required:
            worker_alive = False

        backlog_state = 'idle'
        if dead_letter_jobs > 0:
            backlog_state = f'dead-letter {dead_letter_jobs}'
        elif pending_jobs > 0:
            backlog_state = f'pending {pending_jobs}'

        ok = pong and (not required or bool(worker_alive))
        detail_parts = [backlog_state]
        if heartbeat_age_sec is not None:
            detail_parts.append(f'heartbeat {heartbeat_age_sec:.1f}s ago')
        elif required:
            detail_parts.append('worker heartbeat missing')
        detail = ', '.join(detail_parts)

        return {
            'status': 'pass' if ok else 'fail',
            'ok': ok,
            'enabled': True,
            'required': required,
            'queue': settings.REDIS_PIPELINE_QUEUE,
            'dead_letter_queue': settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE,
            'pending_jobs': pending_jobs,
            'dead_letter_jobs': dead_letter_jobs,
            'worker_heartbeat_key': settings.REDIS_WORKER_HEARTBEAT_KEY,
            'worker_alive': worker_alive,
            'worker_state': heartbeat.get('state'),
            'worker_pipeline_id': heartbeat.get('pipeline_id'),
            'worker_updated_at': heartbeat_updated_at,
            'worker_age_sec': round(heartbeat_age_sec, 3) if heartbeat_age_sec is not None else None,
            'url': settings.REDIS_URL,
            'detail': detail,
        }
    except Exception as exc:
        return {
            'status': 'fail',
            'ok': False,
            'enabled': True,
            'required': required,
            'queue': settings.REDIS_PIPELINE_QUEUE,
            'dead_letter_queue': settings.REDIS_PIPELINE_DEAD_LETTER_QUEUE,
            'url': settings.REDIS_URL,
            'detail': f'{type(exc).__name__}: {exc}',
        }


def collect_health_report() -> dict[str, Any]:
    checks = {
        'app_home': _check_app_home(),
        'disk': _check_disk(),
        'model_file': _check_model_file(),
        'postgresql': _check_postgresql(),
        'redis': _check_redis(),
    }
    ok = all(check.get('ok', False) for check in checks.values())
    return {
        'ok': ok,
        'checked_at': _utc_now(),
        'task_store': task_store.backend_name,
        'pipeline_executor': settings.PIPELINE_EXECUTOR,
        'app_home': str(settings.APP_HOME),
        'checks': checks,
    }


def collect_basic_health() -> dict[str, Any]:
    report = collect_health_report()
    return {
        'ok': report['ok'],
        'task_store': report['task_store'],
        'pipeline_executor': report['pipeline_executor'],
    }
