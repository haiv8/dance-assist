from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.media import router as media_router
from app.api.pipelines import router as pipelines_router
from app.api.reports import router as reports_router
from app.api.system import router as system_router
from app.api.videos import router as videos_router
from app.services.health import collect_basic_health, collect_health_report
from app.services.storage import ensure_dirs
from app.services.task_store import initialize_task_store
from app.settings import settings


def _setup_logging() -> logging.Logger:
    logger = logging.getLogger("dance_assist.api")
    if not logging.getLogger().handlers:
        logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    else:
        logging.getLogger().setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    return logger


def _log_request(logger: logging.Logger, payload: dict) -> None:
    if settings.LOG_JSON:
        logger.info(json.dumps(payload, ensure_ascii=False))
    else:
        logger.info(
            "%s %s %s %sms",
            payload.get("method"),
            payload.get("path"),
            payload.get("status"),
            payload.get("duration_ms"),
        )


def create_app() -> FastAPI:
    ensure_dirs()
    initialize_task_store()

    app = FastAPI(title=settings.APP_NAME)
    logger = _setup_logging()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        started = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]

        response = await call_next(request)

        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        _log_request(
            logger,
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    # Backward-compatible route prefix.
    app.include_router(videos_router, prefix=settings.API_PREFIX)
    app.include_router(pipelines_router, prefix=settings.API_PREFIX)
    app.include_router(reports_router, prefix=settings.API_PREFIX)
    app.include_router(system_router, prefix=settings.API_PREFIX)

    # Versioned route prefix for forward compatibility.
    if settings.ENABLE_V1_ROUTES:
        app.include_router(videos_router, prefix=settings.API_V1_PREFIX)
        app.include_router(pipelines_router, prefix=settings.API_V1_PREFIX)
        app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
        app.include_router(system_router, prefix=settings.API_V1_PREFIX)

    app.include_router(media_router)

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "api_prefix": settings.API_PREFIX,
            "api_v1_prefix": settings.API_V1_PREFIX if settings.ENABLE_V1_ROUTES else None,
            "docs": "/docs",
        }

    @app.get("/health")
    async def health():
        return collect_basic_health()

    @app.get("/health/ready")
    async def health_ready():
        return collect_health_report()

    return app


app = create_app()
