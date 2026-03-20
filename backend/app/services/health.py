from __future__ import annotations

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
    }


def _check_model_file() -> dict[str, Any]:
    runtime_model = settings.MODELS_DIR / 'pose_landmarker_full.task'
    legacy_model = settings.LEGACY_MODELS_DIR / 'pose_landmarker_full.task'
    path = runtime_model if runtime_model.exists() else legacy_model
    exists = path.exists()
    return {
        'status': 'pass' if exists else 'fail',
        'ok': exists,
        'path': str(path),
        'runtime_path': str(runtime_model),
        'legacy_path': str(legacy_model),
        'size_bytes': path.stat().st_size if exists else 0,
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
        }

    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = bool(client.ping())
        pending_jobs = int(client.llen(settings.REDIS_PIPELINE_QUEUE))
        return {
            'status': 'pass' if pong else 'fail',
            'ok': pong,
            'enabled': True,
            'required': required,
            'queue': settings.REDIS_PIPELINE_QUEUE,
            'pending_jobs': pending_jobs,
            'url': settings.REDIS_URL,
        }
    except Exception as exc:
        return {
            'status': 'fail',
            'ok': False,
            'enabled': True,
            'required': required,
            'queue': settings.REDIS_PIPELINE_QUEUE,
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
