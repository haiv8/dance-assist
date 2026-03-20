from __future__ import annotations

import logging
import threading
from typing import Any

from app.settings import settings
from app.services.task_store_repositories import (
    AnalysisReportRepository,
    PipelineEventRepository,
    PipelineTaskRepository,
    VideoRecordRepository,
)

logger = logging.getLogger("dance_assist.task_store")

class PostgresTaskStore:
    def __init__(self, dsn: str, connect_timeout: int = 5) -> None:
        self._dsn = dsn
        self._connect_timeout = max(1, int(connect_timeout))
        self._lock = threading.Lock()
        self._available = False
        self._psycopg = None
        self._initialized = False

    @property
    def is_enabled(self) -> bool:
        return bool(self._dsn)

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def backend_name(self) -> str:
        return "postgresql" if self._available else "file"

    def initialize(self) -> bool:
        if self._initialized:
            return self._available

        self._initialized = True
        if not self.is_enabled:
            return False

        try:
            import psycopg  # type: ignore
        except Exception as exc:
            logger.warning("PostgreSQL task store disabled: psycopg unavailable (%s)", exc)
            self._available = False
            return False

        self._psycopg = psycopg

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS pipeline_tasks (
                            pipeline_id TEXT PRIMARY KEY,
                            pair_name TEXT,
                            status TEXT,
                            stage TEXT,
                            progress DOUBLE PRECISION,
                            teacher_video_id TEXT,
                            user_video_id TEXT,
                            executor TEXT,
                            attempt_count INTEGER,
                            retry_count INTEGER,
                            error_type TEXT,
                            queued_at TIMESTAMPTZ,
                            started_at TIMESTAMPTZ,
                            finished_at TIMESTAMPTZ,
                            score_total DOUBLE PRECISION,
                            confidence_score DOUBLE PRECISION,
                            payload JSONB NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS pair_name TEXT")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS status TEXT")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS stage TEXT")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS progress DOUBLE PRECISION")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS teacher_video_id TEXT")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS user_video_id TEXT")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS executor TEXT")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS attempt_count INTEGER")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS retry_count INTEGER")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS error_type TEXT")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS queued_at TIMESTAMPTZ")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS score_total DOUBLE PRECISION")
                    cur.execute("ALTER TABLE pipeline_tasks ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_tasks_status_updated ON pipeline_tasks (status, updated_at DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_tasks_stage_updated ON pipeline_tasks (stage, updated_at DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_tasks_score_total ON pipeline_tasks (score_total DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_tasks_confidence_score ON pipeline_tasks (confidence_score DESC)")
                    cur.execute(
                        """
                        UPDATE pipeline_tasks
                        SET
                            pair_name = COALESCE(pair_name, NULLIF(payload->>'pair_name', '')),
                            status = COALESCE(status, NULLIF(payload->>'status', '')),
                            stage = COALESCE(stage, NULLIF(payload->>'stage', '')),
                            progress = COALESCE(progress, NULLIF(payload->>'progress', '')::double precision),
                            teacher_video_id = COALESCE(teacher_video_id, NULLIF(payload->>'teacher_video_id', '')),
                            user_video_id = COALESCE(user_video_id, NULLIF(payload->>'user_video_id', '')),
                            executor = COALESCE(executor, NULLIF(payload->>'executor', '')),
                            attempt_count = COALESCE(attempt_count, NULLIF(payload->>'attempt_count', '')::integer),
                            retry_count = COALESCE(retry_count, NULLIF(payload->>'retry_count', '')::integer),
                            error_type = COALESCE(error_type, NULLIF(payload->>'error_type', '')),
                            queued_at = COALESCE(queued_at, NULLIF(payload->>'queued_at', '')::timestamptz),
                            started_at = COALESCE(started_at, NULLIF(payload->>'started_at', '')::timestamptz),
                            finished_at = COALESCE(finished_at, NULLIF(payload->>'finished_at', '')::timestamptz),
                            score_total = COALESCE(
                                score_total,
                                NULLIF(payload->'report'->>'score_0_100', '')::double precision,
                                NULLIF(payload->'report'->'scores'->>'score_total', '')::double precision
                            ),
                            confidence_score = COALESCE(
                                confidence_score,
                                NULLIF(payload->'report'->'confidence'->>'score', '')::double precision
                            )
                        WHERE
                            pair_name IS NULL
                            OR status IS NULL
                            OR stage IS NULL
                            OR teacher_video_id IS NULL
                            OR user_video_id IS NULL
                            OR score_total IS NULL
                            OR confidence_score IS NULL
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS analysis_reports (
                            pipeline_id TEXT PRIMARY KEY,
                            pair_name TEXT,
                            teacher_video_id TEXT,
                            user_video_id TEXT,
                            status TEXT,
                            stage TEXT,
                            executor TEXT,
                            queued_at TIMESTAMPTZ,
                            started_at TIMESTAMPTZ,
                            finished_at TIMESTAMPTZ,
                            score_total DOUBLE PRECISION,
                            score_pose DOUBLE PRECISION,
                            score_tempo DOUBLE PRECISION,
                            confidence_score DOUBLE PRECISION,
                            confidence_level TEXT,
                            overall_advice TEXT,
                            confidence_summary TEXT,
                            beginner_summary TEXT,
                            teaching_summary TEXT,
                            top_joints JSONB NOT NULL DEFAULT '[]'::jsonb,
                            files JSONB NOT NULL DEFAULT '{}'::jsonb,
                            report_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS pair_name TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS teacher_video_id TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS user_video_id TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS status TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS stage TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS executor TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS queued_at TIMESTAMPTZ")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS score_total DOUBLE PRECISION")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS score_pose DOUBLE PRECISION")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS score_tempo DOUBLE PRECISION")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS confidence_level TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS overall_advice TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS confidence_summary TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS beginner_summary TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS teaching_summary TEXT")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS top_joints JSONB NOT NULL DEFAULT '[]'::jsonb")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS files JSONB NOT NULL DEFAULT '{}'::jsonb")
                    cur.execute("ALTER TABLE analysis_reports ADD COLUMN IF NOT EXISTS report_payload JSONB NOT NULL DEFAULT '{}'::jsonb")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_reports_finished_at ON analysis_reports (finished_at DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_reports_score_total ON analysis_reports (score_total DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_reports_confidence_score ON analysis_reports (confidence_score DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_reports_pair_name ON analysis_reports (pair_name)")
                    cur.execute(
                        """
                        INSERT INTO analysis_reports (
                            pipeline_id,
                            pair_name,
                            teacher_video_id,
                            user_video_id,
                            status,
                            stage,
                            executor,
                            queued_at,
                            started_at,
                            finished_at,
                            score_total,
                            score_pose,
                            score_tempo,
                            confidence_score,
                            confidence_level,
                            overall_advice,
                            confidence_summary,
                            beginner_summary,
                            teaching_summary,
                            top_joints,
                            files,
                            report_payload,
                            created_at,
                            updated_at
                        )
                        SELECT
                            pipeline_id,
                            COALESCE(pair_name, NULLIF(payload->>'pair_name', '')),
                            COALESCE(teacher_video_id, NULLIF(payload->>'teacher_video_id', '')),
                            COALESCE(user_video_id, NULLIF(payload->>'user_video_id', '')),
                            COALESCE(status, NULLIF(payload->>'status', '')),
                            COALESCE(stage, NULLIF(payload->>'stage', '')),
                            COALESCE(executor, NULLIF(payload->>'executor', '')),
                            COALESCE(queued_at, NULLIF(payload->>'queued_at', '')::timestamptz),
                            COALESCE(started_at, NULLIF(payload->>'started_at', '')::timestamptz),
                            COALESCE(finished_at, NULLIF(payload->>'finished_at', '')::timestamptz),
                            COALESCE(
                                score_total,
                                NULLIF(payload->'report'->>'score_0_100', '')::double precision,
                                NULLIF(payload->'report'->'scores'->>'score_total', '')::double precision
                            ),
                            NULLIF(payload->'report'->'scores'->>'score_pose', '')::double precision,
                            NULLIF(payload->'report'->'scores'->>'score_tempo', '')::double precision,
                            COALESCE(
                                confidence_score,
                                NULLIF(payload->'report'->'confidence'->>'score', '')::double precision
                            ),
                            NULLIF(payload->'report'->'confidence'->>'level', ''),
                            NULLIF(payload->'report'->'recommendations'->>'overall', ''),
                            NULLIF(payload->'report'->'confidence'->>'summary', ''),
                            NULLIF(payload->'report'->'beginner_report'->>'summary', ''),
                            NULLIF(payload->'report'->'teaching_report'->>'summary', ''),
                            COALESCE(payload->'report'->'top_joints', '[]'::jsonb),
                            COALESCE(payload->'files', '{}'::jsonb),
                            COALESCE(payload->'report', '{}'::jsonb),
                            COALESCE(created_at, NOW()),
                            NOW()
                        FROM pipeline_tasks
                        WHERE (payload ? 'report' OR payload ? 'files' OR status = 'done')
                        ON CONFLICT (pipeline_id) DO UPDATE SET
                            pair_name = EXCLUDED.pair_name,
                            teacher_video_id = EXCLUDED.teacher_video_id,
                            user_video_id = EXCLUDED.user_video_id,
                            status = EXCLUDED.status,
                            stage = EXCLUDED.stage,
                            executor = EXCLUDED.executor,
                            queued_at = COALESCE(EXCLUDED.queued_at, analysis_reports.queued_at),
                            started_at = COALESCE(EXCLUDED.started_at, analysis_reports.started_at),
                            finished_at = COALESCE(EXCLUDED.finished_at, analysis_reports.finished_at),
                            score_total = COALESCE(EXCLUDED.score_total, analysis_reports.score_total),
                            score_pose = COALESCE(EXCLUDED.score_pose, analysis_reports.score_pose),
                            score_tempo = COALESCE(EXCLUDED.score_tempo, analysis_reports.score_tempo),
                            confidence_score = COALESCE(EXCLUDED.confidence_score, analysis_reports.confidence_score),
                            confidence_level = COALESCE(EXCLUDED.confidence_level, analysis_reports.confidence_level),
                            overall_advice = COALESCE(EXCLUDED.overall_advice, analysis_reports.overall_advice),
                            confidence_summary = COALESCE(EXCLUDED.confidence_summary, analysis_reports.confidence_summary),
                            beginner_summary = COALESCE(EXCLUDED.beginner_summary, analysis_reports.beginner_summary),
                            teaching_summary = COALESCE(EXCLUDED.teaching_summary, analysis_reports.teaching_summary),
                            top_joints = EXCLUDED.top_joints,
                            files = EXCLUDED.files,
                            report_payload = EXCLUDED.report_payload,
                            updated_at = NOW()
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS pipeline_frame_analysis (
                            pipeline_id TEXT NOT NULL,
                            frame INTEGER NOT NULL,
                            sec DOUBLE PRECISION,
                            frame_error DOUBLE PRECISION,
                            marker_type TEXT,
                            severity TEXT,
                            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            PRIMARY KEY (pipeline_id, frame)
                        )
                        """
                    )
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_frame_analysis_pipeline_sec ON pipeline_frame_analysis (pipeline_id, sec, frame)")
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS video_records (
                            video_id TEXT PRIMARY KEY,
                            role TEXT NOT NULL,
                            filename TEXT NOT NULL,
                            uploaded_at TIMESTAMPTZ NOT NULL,
                            size_bytes BIGINT NOT NULL,
                            video_path TEXT NOT NULL,
                            url TEXT NOT NULL,
                            payload JSONB NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS pipeline_task_events (
                            event_id BIGSERIAL PRIMARY KEY,
                            pipeline_id TEXT NOT NULL,
                            event_type TEXT NOT NULL,
                            status TEXT,
                            message TEXT,
                            executor TEXT,
                            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                conn.commit()
        except Exception as exc:
            logger.warning("PostgreSQL task store disabled: schema init failed (%s)", exc)
            self._available = False
            return False

        self._available = True
        self._repair_analysis_reports_from_outputs()
        return True

    def save_task(self, task: dict[str, Any]) -> bool:
        if not self._available:
            return False
        return task_repository.save(task, on_after_upsert=report_repository.save_with_cursor)

    def load_task(self, pipeline_id: str) -> dict[str, Any] | None:
        if not self._available:
            return None
        return task_repository.load(pipeline_id)

    def _save_analysis_report_with_cursor(self, cur, task: dict[str, Any]) -> None:
        if not self._available:
            return
        report_repository.save_with_cursor(cur, task)

    def _save_frame_analysis_with_cursor(self, cur, task: dict[str, Any]) -> None:
        if not self._available:
            return
        report_repository.save_frame_analysis_with_cursor(cur, task)

    def load_analysis_report(self, pipeline_id: str) -> dict[str, Any] | None:
        if not self._available:
            return None
        return report_repository.load(pipeline_id)

    def load_frame_analysis_range(
        self,
        pipeline_id: str,
        *,
        start_frame: int,
        end_frame: int,
    ) -> list[dict[str, Any]]:
        if not self._available:
            return []
        return report_repository.load_frame_range(
            pipeline_id,
            start_frame=start_frame,
            end_frame=end_frame,
        )

    def list_analysis_reports(
        self,
        *,
        limit: int = 50,
        query: str | None = None,
        min_score: float | None = None,
        min_confidence: float | None = None,
    ) -> list[dict[str, Any]]:
        if not self._available:
            return []
        return report_repository.list_reports(
            limit=limit,
            query=query,
            min_score=min_score,
            min_confidence=min_confidence,
        )

    def _repair_analysis_reports_from_outputs(self) -> None:
        if not self._available:
            return
        report_repository.repair_from_outputs()

    def _connect(self):
        if self._psycopg is None:
            raise RuntimeError("psycopg is not initialized")
        return self._psycopg.connect(self._dsn, connect_timeout=self._connect_timeout)

task_store = PostgresTaskStore(
    dsn=settings.DATABASE_URL,
    connect_timeout=settings.DATABASE_CONNECT_TIMEOUT_SEC,
)
task_repository = PipelineTaskRepository(lambda: task_store._connect(), task_store._lock, logger)
report_repository = AnalysisReportRepository(lambda: task_store._connect(), task_store._lock, logger)
video_repository = VideoRecordRepository(lambda: task_store._connect(), task_store._lock, logger)
event_repository = PipelineEventRepository(lambda: task_store._connect(), task_store._lock, logger)

def initialize_task_store() -> bool:
    return task_store.initialize()

def _ensure_task_store_ready() -> None:
    if not task_store.is_available and task_store.is_enabled:
        task_store.initialize()

def save_task_record(task: dict[str, Any]) -> bool:
    _ensure_task_store_ready()
    return task_repository.save(task, on_after_upsert=report_repository.save_with_cursor)

def load_task_record(pipeline_id: str) -> dict[str, Any] | None:
    _ensure_task_store_ready()
    return task_repository.load(pipeline_id)

def get_task_store_backend() -> str:
    _ensure_task_store_ready()
    return task_store.backend_name

def list_task_summaries(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return []
    return task_repository.list_summaries(limit=limit, status=status)

def load_analysis_report_record(pipeline_id: str) -> dict[str, Any] | None:
    _ensure_task_store_ready()
    return report_repository.load(pipeline_id)

def load_frame_analysis_range(
    pipeline_id: str,
    *,
    start_frame: int,
    end_frame: int,
) -> list[dict[str, Any]]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return []
    return report_repository.load_frame_range(
        pipeline_id,
        start_frame=start_frame,
        end_frame=end_frame,
    )

def list_analysis_reports(
    limit: int = 50,
    query: str | None = None,
    min_score: float | None = None,
    min_confidence: float | None = None,
) -> list[dict[str, Any]]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return []
    return report_repository.list_reports(
        limit=limit,
        query=query,
        min_score=min_score,
        min_confidence=min_confidence,
    )

def repair_analysis_report_records() -> bool:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return False
    report_repository.repair_from_outputs()
    return True

def save_video_record(meta: dict[str, Any]) -> bool:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return False
    return video_repository.save(meta)

def load_video_record(video_id: str, role: str | None = None) -> dict[str, Any] | None:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return None
    return video_repository.load(video_id, role=role)

def list_video_records(role: str | None = None) -> list[dict[str, Any]]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return []
    return video_repository.list(role=role)

def delete_video_record(video_id: str, role: str | None = None) -> bool:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return False
    return video_repository.delete(video_id, role=role)

def save_pipeline_event(
    pipeline_id: str,
    event_type: str,
    *,
    status: str | None = None,
    message: str | None = None,
    executor: str | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return False
    return event_repository.save(
        pipeline_id,
        event_type,
        status=status,
        message=message,
        executor=executor,
        payload=payload,
    )

def get_pipeline_failure_stats(days: int = 30, limit: int = 20) -> dict[str, Any]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return {
            "window_days": max(1, int(days)),
            "total_failures": 0,
            "by_error_type": [],
            "by_executor": [],
            "recent_failures": [],
        }
    return event_repository.failure_stats(days=days, limit=limit)
