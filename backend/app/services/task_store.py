from __future__ import annotations

import json
import logging
import threading
from typing import Any

from app.settings import settings

logger = logging.getLogger("dance_assist.task_store")


def _as_db_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if out == out else None


def _as_db_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _task_report_score(task: dict[str, Any]) -> float | None:
    report = task.get("report")
    if isinstance(report, dict):
        score = report.get("score_0_100")
        if score is None:
            scores = report.get("scores")
            if isinstance(scores, dict):
                score = scores.get("score_total")
        return _as_db_float(score)
    return None


def _task_confidence_score(task: dict[str, Any]) -> float | None:
    report = task.get("report")
    if isinstance(report, dict):
        confidence = report.get("confidence")
        if isinstance(confidence, dict):
            return _as_db_float(confidence.get("score"))
    return None


def _json_ready_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _json_ready_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _confidence_level_from_score(value: Any) -> str | None:
    score = _as_db_float(value)
    if score is None:
        return None
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _load_output_summary(pair_name: str | None) -> dict[str, Any]:
    if not pair_name:
        return {}
    path = settings.OUTPUTS_DIR / str(pair_name).strip() / "summary.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ensure_summary_url(files: dict[str, Any], pair_name: str | None) -> dict[str, Any]:
    if not pair_name:
        return dict(files)
    out = dict(files)
    if "summary_url" not in out and (settings.OUTPUTS_DIR / str(pair_name).strip() / "summary.json").exists():
        out["summary_url"] = f"/artifacts/{pair_name}/summary.json"
    return out


def _derive_confidence_from_report(report: dict[str, Any], summary: dict[str, Any]) -> tuple[float | None, str | None, str | None]:
    quality = _json_ready_dict(report.get("quality_stats"))
    align = _json_ready_dict(report.get("alignment_quality"))
    tempo = _json_ready_dict(report.get("tempo"))

    teacher_invalid = _as_db_float(quality.get("teacher_invalid_ratio"))
    user_invalid = _as_db_float(quality.get("user_invalid_ratio"))
    teacher_low = _as_db_float(quality.get("teacher_low_conf_ratio"))
    user_low = _as_db_float(quality.get("user_low_conf_ratio"))
    teacher_gap = _as_db_float(quality.get("teacher_long_gap_ratio"))
    user_gap = _as_db_float(quality.get("user_long_gap_ratio"))
    teacher_mean = _as_db_float(quality.get("teacher_mean_quality"))
    user_mean = _as_db_float(quality.get("user_mean_quality"))

    if teacher_invalid is None:
        teacher_invalid = _as_db_float(summary.get("quality_low_conf_ratio"))
    if user_invalid is None:
        user_invalid = teacher_invalid
    if teacher_low is None:
        teacher_low = teacher_invalid
    if user_low is None:
        user_low = teacher_low
    if teacher_gap is None:
        teacher_gap = 0.0
    if user_gap is None:
        user_gap = teacher_gap
    if teacher_mean is None:
        teacher_mean = max(0.0, min(1.0, 1.0 - (teacher_invalid or 0.0)))
    if user_mean is None:
        user_mean = max(0.0, min(1.0, 1.0 - (user_invalid or 0.0)))

    jump_rate = _as_db_float(align.get("jump_rate"))
    warp_ratio = _as_db_float(align.get("warp_ratio"))
    deviation_area = _as_db_float(tempo.get("deviation_area"))
    fallback_linear = bool(align.get("fallback_linear_map_applied"))

    if None in (teacher_invalid, user_invalid, teacher_low, user_low, jump_rate, warp_ratio):
        return None, None, None

    tracking_quality = max(0.0, min(1.0,
        0.3 * ((teacher_mean + user_mean) / 2.0)
        + 0.4 * (1.0 - ((teacher_invalid + user_invalid) / 2.0))
        + 0.3 * (1.0 - ((teacher_low + user_low) / 2.0))
    ))

    jump_penalty = max(0.0, min(1.0, jump_rate / 0.45))
    warp_penalty = max(0.0, min(1.0, abs(warp_ratio - 1.0) / 0.9))
    alignment_stability = max(0.0, min(1.0, 1.0 - (0.7 * jump_penalty + 0.3 * warp_penalty)))
    if fallback_linear:
        alignment_stability *= 0.55

    if deviation_area is None:
        tempo_stability = 0.5
    else:
        tempo_stability = max(0.0, min(1.0, 1.0 - (deviation_area / 0.12)))

    score = max(0.0, min(1.0, 0.5 * tracking_quality + 0.3 * alignment_stability + 0.2 * tempo_stability))
    level = _confidence_level_from_score(score)

    max_invalid = max(teacher_invalid, user_invalid)
    max_gap = max(teacher_gap or 0.0, user_gap or 0.0)
    notes: list[str] = []
    if max_invalid >= 0.35:
        notes.append("跟踪覆盖率偏低")
    elif max_invalid >= 0.22:
        notes.append("部分片段跟踪不稳定")
    if max_gap >= 0.10:
        notes.append("存在较长遮挡区间")
    if fallback_linear or jump_rate >= 0.35:
        notes.append("动作对齐稳定性一般")
    if tempo_stability < 0.6:
        notes.append("节奏判断可信度偏低")

    if level == "high":
        summary_text = "本次分析可信度较高，可直接参考结果进行复盘。"
    elif level == "medium":
        summary_text = "本次分析可信度中等，建议结合原视频一起判断。"
    else:
        summary_text = "本次分析可信度较低，建议优先改善拍摄和跟踪质量后再复测。"

    if notes:
        summary_text = f"{summary_text} 影响因素：{'、'.join(notes[:3])}。"

    if summary.get("confidence_summary"):
        summary_text = str(summary.get("confidence_summary"))
    if summary.get("confidence_level"):
        level = str(summary.get("confidence_level"))
    if summary.get("confidence_score") is not None:
        score = _as_db_float(summary.get("confidence_score")) or score

    return score, level, summary_text


def _task_report_row(task: dict[str, Any]) -> dict[str, Any] | None:
    report = _json_ready_dict(task.get("report"))
    pair_name = str(task.get("pair_name", "")).strip() or None
    summary = _load_output_summary(pair_name)
    files = _ensure_summary_url(_json_ready_dict(task.get("files")), pair_name)
    if not report and not files and str(task.get("status", "")).strip() != "done":
        return None

    scores = _json_ready_dict(report.get("scores"))
    confidence = _json_ready_dict(report.get("confidence"))
    recommendations = _json_ready_dict(report.get("recommendations"))
    beginner_report = _json_ready_dict(report.get("beginner_report"))
    teaching_report = _json_ready_dict(report.get("teaching_report"))

    confidence_score = _task_confidence_score(task)
    if confidence_score is None:
        confidence_score = _as_db_float(summary.get("confidence_score"))
    derived_score, derived_level, derived_summary = _derive_confidence_from_report(report, summary)
    confidence_score = confidence_score if confidence_score is not None else derived_score

    return {
        "pipeline_id": str(task.get("pipeline_id", "")).strip(),
        "pair_name": pair_name,
        "teacher_video_id": str(task.get("teacher_video_id", "")).strip() or None,
        "user_video_id": str(task.get("user_video_id", "")).strip() or None,
        "status": str(task.get("status", "")).strip() or None,
        "stage": str(task.get("stage", "")).strip() or None,
        "executor": str(task.get("executor", "")).strip() or None,
        "queued_at": str(task.get("queued_at", "")).strip() or None,
        "started_at": str(task.get("started_at", "")).strip() or None,
        "finished_at": str(task.get("finished_at", "")).strip() or None,
        "score_total": _task_report_score(task) or _as_db_float(summary.get("score_total")),
        "score_pose": _as_db_float(scores.get("score_pose")) or _as_db_float(summary.get("score_pose")),
        "score_tempo": _as_db_float(scores.get("score_tempo")) or _as_db_float(summary.get("score_tempo")),
        "confidence_score": confidence_score,
        "confidence_level": str(confidence.get("level", "")).strip() or str(summary.get("confidence_level", "")).strip() or derived_level or _confidence_level_from_score(confidence_score),
        "overall_advice": str(recommendations.get("overall", "")).strip() or None,
        "confidence_summary": str(confidence.get("summary", "")).strip() or str(summary.get("confidence_summary", "")).strip() or derived_summary,
        "beginner_summary": str(beginner_report.get("summary", "")).strip() or None,
        "teaching_summary": str(teaching_report.get("summary", "")).strip() or None,
        "top_joints": _json_ready_list(report.get("top_joints")),
        "files": files,
        "report_payload": report,
    }


def _structured_task_row(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "pipeline_id": str(task.get("pipeline_id", "")).strip(),
        "pair_name": str(task.get("pair_name", "")).strip() or None,
        "status": str(task.get("status", "")).strip() or None,
        "stage": str(task.get("stage", "")).strip() or None,
        "progress": _as_db_float(task.get("progress")),
        "teacher_video_id": str(task.get("teacher_video_id", "")).strip() or None,
        "user_video_id": str(task.get("user_video_id", "")).strip() or None,
        "executor": str(task.get("executor", "")).strip() or None,
        "attempt_count": _as_db_int(task.get("attempt_count")),
        "retry_count": _as_db_int(task.get("retry_count")),
        "error_type": str(task.get("error_type", "")).strip() or None,
        "queued_at": str(task.get("queued_at", "")).strip() or None,
        "started_at": str(task.get("started_at", "")).strip() or None,
        "finished_at": str(task.get("finished_at", "")).strip() or None,
        "score_total": _task_report_score(task),
        "confidence_score": _task_confidence_score(task),
    }


def _merge_task_payload(payload: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    task = dict(payload)
    for key in (
        "pipeline_id",
        "pair_name",
        "status",
        "stage",
        "progress",
        "teacher_video_id",
        "user_video_id",
        "executor",
        "attempt_count",
        "retry_count",
        "error_type",
        "queued_at",
        "started_at",
        "finished_at",
    ):
        value = row.get(key)
        if value is not None and task.get(key) in (None, ""):
            task[key] = value
    return task


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

        row = _structured_task_row(task)
        pipeline_id = row["pipeline_id"]
        if not pipeline_id:
            return False

        payload = json.dumps(task, ensure_ascii=False)
        try:
            with self._lock:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO pipeline_tasks (
                                pipeline_id,
                                pair_name,
                                status,
                                stage,
                                progress,
                                teacher_video_id,
                                user_video_id,
                                executor,
                                attempt_count,
                                retry_count,
                                error_type,
                                queued_at,
                                started_at,
                                finished_at,
                                score_total,
                                confidence_score,
                                payload,
                                created_at,
                                updated_at
                            )
                            VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s::timestamptz, %s::timestamptz, %s::timestamptz,
                                %s, %s, %s::jsonb, NOW(), NOW()
                            )
                            ON CONFLICT (pipeline_id)
                            DO UPDATE SET
                                pair_name = EXCLUDED.pair_name,
                                status = EXCLUDED.status,
                                stage = EXCLUDED.stage,
                                progress = EXCLUDED.progress,
                                teacher_video_id = EXCLUDED.teacher_video_id,
                                user_video_id = EXCLUDED.user_video_id,
                                executor = EXCLUDED.executor,
                                attempt_count = EXCLUDED.attempt_count,
                                retry_count = EXCLUDED.retry_count,
                                error_type = EXCLUDED.error_type,
                                queued_at = COALESCE(EXCLUDED.queued_at, pipeline_tasks.queued_at),
                                started_at = COALESCE(EXCLUDED.started_at, pipeline_tasks.started_at),
                                finished_at = EXCLUDED.finished_at,
                                score_total = EXCLUDED.score_total,
                                confidence_score = EXCLUDED.confidence_score,
                                payload = EXCLUDED.payload,
                                updated_at = NOW()
                            """,
                            (
                                pipeline_id,
                                row["pair_name"],
                                row["status"],
                                row["stage"],
                                row["progress"],
                                row["teacher_video_id"],
                                row["user_video_id"],
                                row["executor"],
                                row["attempt_count"],
                                row["retry_count"],
                                row["error_type"],
                                row["queued_at"],
                                row["started_at"],
                                row["finished_at"],
                                row["score_total"],
                                row["confidence_score"],
                                payload,
                            ),
                        )
                        self._save_analysis_report_with_cursor(cur, task)
                    conn.commit()
            return True
        except Exception as exc:
            logger.warning("PostgreSQL task store write failed for %s: %s", pipeline_id, exc)
            return False

    def load_task(self, pipeline_id: str) -> dict[str, Any] | None:
        if not self._available:
            return None

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            pipeline_id,
                            pair_name,
                            status,
                            stage,
                            progress,
                            teacher_video_id,
                            user_video_id,
                            executor,
                            attempt_count,
                            retry_count,
                            error_type,
                            queued_at,
                            started_at,
                            finished_at,
                            score_total,
                            confidence_score,
                            payload::text
                        FROM pipeline_tasks
                        WHERE pipeline_id = %s
                        """,
                        (pipeline_id,),
                    )
                    row = cur.fetchone()
            if not row or not row[-1]:
                return None
            payload = json.loads(row[-1])
            structured = {
                "pipeline_id": row[0],
                "pair_name": row[1],
                "status": row[2],
                "stage": row[3],
                "progress": row[4],
                "teacher_video_id": row[5],
                "user_video_id": row[6],
                "executor": row[7],
                "attempt_count": row[8],
                "retry_count": row[9],
                "error_type": row[10],
                "queued_at": row[11].isoformat() if row[11] is not None else None,
                "started_at": row[12].isoformat() if row[12] is not None else None,
                "finished_at": row[13].isoformat() if row[13] is not None else None,
                "score_total": row[14],
                "confidence_score": row[15],
            }
            return _merge_task_payload(payload, structured)
        except Exception as exc:
            logger.warning("PostgreSQL task store read failed for %s: %s", pipeline_id, exc)
            return None

    def _save_analysis_report_with_cursor(self, cur, task: dict[str, Any]) -> None:
        row = _task_report_row(task)
        if not row or not row["pipeline_id"]:
            return

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
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s::timestamptz, %s::timestamptz, %s::timestamptz,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s::jsonb, %s::jsonb, %s::jsonb, NOW(), NOW()
            )
            ON CONFLICT (pipeline_id)
            DO UPDATE SET
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
            """,
            (
                row["pipeline_id"],
                row["pair_name"],
                row["teacher_video_id"],
                row["user_video_id"],
                row["status"],
                row["stage"],
                row["executor"],
                row["queued_at"],
                row["started_at"],
                row["finished_at"],
                row["score_total"],
                row["score_pose"],
                row["score_tempo"],
                row["confidence_score"],
                row["confidence_level"],
                row["overall_advice"],
                row["confidence_summary"],
                row["beginner_summary"],
                row["teaching_summary"],
                json.dumps(row["top_joints"], ensure_ascii=False),
                json.dumps(row["files"], ensure_ascii=False),
                json.dumps(row["report_payload"], ensure_ascii=False),
            ),
        )

    def load_analysis_report(self, pipeline_id: str) -> dict[str, Any] | None:
        if not self._available:
            return None

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
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
                            top_joints::text,
                            files::text,
                            report_payload::text,
                            created_at,
                            updated_at
                        FROM analysis_reports
                        WHERE pipeline_id = %s
                        """,
                        (pipeline_id,),
                    )
                    row = cur.fetchone()
            if not row:
                return None
            return {
                "pipeline_id": row[0],
                "pair_name": row[1],
                "teacher_video_id": row[2],
                "user_video_id": row[3],
                "status": row[4],
                "stage": row[5],
                "executor": row[6],
                "queued_at": row[7].isoformat() if row[7] is not None else None,
                "started_at": row[8].isoformat() if row[8] is not None else None,
                "finished_at": row[9].isoformat() if row[9] is not None else None,
                "score_total": row[10],
                "score_pose": row[11],
                "score_tempo": row[12],
                "confidence_score": row[13],
                "confidence_level": row[14] or _confidence_level_from_score(row[13]),
                "overall_advice": row[15],
                "confidence_summary": row[16],
                "beginner_summary": row[17],
                "teaching_summary": row[18],
                "top_joints": json.loads(row[19]) if row[19] else [],
                "files": json.loads(row[20]) if row[20] else {},
                "report": json.loads(row[21]) if row[21] else {},
                "created_at": row[22].isoformat() if row[22] is not None else None,
                "updated_at": row[23].isoformat() if row[23] is not None else None,
            }
        except Exception as exc:
            logger.warning("PostgreSQL analysis report read failed for %s: %s", pipeline_id, exc)
            return None

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

        safe_limit = max(1, min(500, int(limit)))
        clauses = ["status = 'done'"]
        params: list[Any] = []

        if query:
            clauses.append("(pair_name ILIKE %s OR teacher_video_id ILIKE %s OR user_video_id ILIKE %s)")
            needle = f"%{query.strip()}%"
            params.extend([needle, needle, needle])
        if min_score is not None:
            clauses.append("score_total >= %s")
            params.append(float(min_score))
        if min_confidence is not None:
            clauses.append("confidence_score >= %s")
            params.append(float(min_confidence))

        where_sql = " AND ".join(clauses)
        sql = f"""
            SELECT
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
                top_joints::text,
                files::text,
                updated_at
            FROM analysis_reports
            WHERE {where_sql}
            ORDER BY COALESCE(finished_at, updated_at) DESC
            LIMIT %s
        """
        params.append(safe_limit)

        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(params))
                    rows = cur.fetchall()
            return [
                {
                    "pipeline_id": row[0],
                    "pair_name": row[1],
                    "teacher_video_id": row[2],
                    "user_video_id": row[3],
                    "status": row[4],
                    "stage": row[5],
                    "executor": row[6],
                    "queued_at": row[7].isoformat() if row[7] is not None else None,
                    "started_at": row[8].isoformat() if row[8] is not None else None,
                    "finished_at": row[9].isoformat() if row[9] is not None else None,
                    "score_total": row[10],
                    "score_pose": row[11],
                    "score_tempo": row[12],
                    "confidence_score": row[13],
                    "confidence_level": row[14] or _confidence_level_from_score(row[13]),
                    "overall_advice": row[15],
                    "confidence_summary": row[16],
                    "beginner_summary": row[17],
                    "teaching_summary": row[18],
                    "top_joints": json.loads(row[19]) if row[19] else [],
                    "files": json.loads(row[20]) if row[20] else {},
                    "updated_at": row[21].isoformat() if row[21] is not None else None,
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("PostgreSQL analysis report query failed: %s", exc)
            return []

    def _repair_analysis_reports_from_outputs(self) -> None:
        if not self._available:
            return

        try:
            with self._lock:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT pipeline_id, pair_name, files::text, report_payload::text
                            FROM analysis_reports
                            WHERE
                                score_pose IS NULL
                                OR score_tempo IS NULL
                                OR confidence_score IS NULL
                                OR confidence_level IS NULL
                                OR confidence_summary IS NULL
                                OR NOT (files ? 'summary_url')
                            """
                        )
                        rows = cur.fetchall()

                        for pipeline_id, pair_name, files_text, report_text in rows:
                            summary = _load_output_summary(pair_name)
                            existing_files = json.loads(files_text) if files_text else {}
                            files = _ensure_summary_url(existing_files, pair_name)
                            report_payload = json.loads(report_text) if report_text else {}
                            derived_score, derived_level, derived_summary = _derive_confidence_from_report(
                                report_payload if isinstance(report_payload, dict) else {},
                                summary,
                            )
                            if not summary and files == existing_files and derived_score is None and derived_summary is None:
                                continue

                            confidence_score = _as_db_float(summary.get("confidence_score"))
                            if confidence_score is None:
                                confidence_score = derived_score
                            confidence_level = str(summary.get("confidence_level", "")).strip() or derived_level or _confidence_level_from_score(confidence_score)
                            confidence_summary = str(summary.get("confidence_summary", "")).strip() or derived_summary or None
                            score_pose = _as_db_float(summary.get("score_pose"))
                            score_tempo = _as_db_float(summary.get("score_tempo"))

                            cur.execute(
                                """
                                UPDATE analysis_reports
                                SET
                                    score_pose = CASE WHEN %s IS NOT NULL THEN %s ELSE score_pose END,
                                    score_tempo = CASE WHEN %s IS NOT NULL THEN %s ELSE score_tempo END,
                                    confidence_score = CASE WHEN %s IS NOT NULL THEN %s ELSE confidence_score END,
                                    confidence_level = CASE WHEN %s::text IS NOT NULL AND %s::text <> '' THEN %s::text ELSE confidence_level END,
                                    confidence_summary = CASE WHEN %s::text IS NOT NULL AND %s::text <> '' THEN %s::text ELSE confidence_summary END,
                                    files = %s::jsonb,
                                    updated_at = NOW()
                                WHERE pipeline_id = %s
                                """,
                                (
                                    score_pose,
                                    score_pose,
                                    score_tempo,
                                    score_tempo,
                                    confidence_score,
                                    confidence_score,
                                    confidence_level,
                                    confidence_level,
                                    confidence_level,
                                    confidence_summary,
                                    confidence_summary,
                                    confidence_summary,
                                    json.dumps(files, ensure_ascii=False),
                                    pipeline_id,
                                ),
                            )
                    conn.commit()
        except Exception as exc:
            logger.warning("PostgreSQL analysis report repair failed: %s", exc)

    def _connect(self):
        if self._psycopg is None:
            raise RuntimeError("psycopg is not initialized")
        return self._psycopg.connect(self._dsn, connect_timeout=self._connect_timeout)


task_store = PostgresTaskStore(
    dsn=settings.DATABASE_URL,
    connect_timeout=settings.DATABASE_CONNECT_TIMEOUT_SEC,
)


def initialize_task_store() -> bool:
    return task_store.initialize()


def _ensure_task_store_ready() -> None:
    if not task_store.is_available and task_store.is_enabled:
        task_store.initialize()


def save_task_record(task: dict[str, Any]) -> bool:
    _ensure_task_store_ready()
    return task_store.save_task(task)


def load_task_record(pipeline_id: str) -> dict[str, Any] | None:
    _ensure_task_store_ready()
    return task_store.load_task(pipeline_id)


def get_task_store_backend() -> str:
    _ensure_task_store_ready()
    return task_store.backend_name


def list_task_summaries(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return []

    safe_limit = max(1, min(500, int(limit)))
    try:
        with task_store._connect() as conn:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        """
                        SELECT
                            pipeline_id,
                            pair_name,
                            status,
                            stage,
                            progress,
                            teacher_video_id,
                            user_video_id,
                            executor,
                            attempt_count,
                            retry_count,
                            error_type,
                            queued_at,
                            started_at,
                            finished_at,
                            score_total,
                            confidence_score,
                            updated_at
                        FROM pipeline_tasks
                        WHERE status = %s
                        ORDER BY updated_at DESC
                        LIMIT %s
                        """,
                        (status, safe_limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            pipeline_id,
                            pair_name,
                            status,
                            stage,
                            progress,
                            teacher_video_id,
                            user_video_id,
                            executor,
                            attempt_count,
                            retry_count,
                            error_type,
                            queued_at,
                            started_at,
                            finished_at,
                            score_total,
                            confidence_score,
                            updated_at
                        FROM pipeline_tasks
                        ORDER BY updated_at DESC
                        LIMIT %s
                        """,
                        (safe_limit,),
                    )
                rows = cur.fetchall()
        return [
            {
                "pipeline_id": row[0],
                "pair_name": row[1],
                "status": row[2],
                "stage": row[3],
                "progress": row[4],
                "teacher_video_id": row[5],
                "user_video_id": row[6],
                "executor": row[7],
                "attempt_count": row[8],
                "retry_count": row[9],
                "error_type": row[10],
                "queued_at": row[11].isoformat() if row[11] is not None else None,
                "started_at": row[12].isoformat() if row[12] is not None else None,
                "finished_at": row[13].isoformat() if row[13] is not None else None,
                "score_total": row[14],
                "confidence_score": row[15],
                "updated_at": row[16].isoformat() if row[16] is not None else None,
            }
            for row in rows
        ]
    except Exception as exc:
        logger.warning("PostgreSQL pipeline task summary query failed: %s", exc)
        return []


def load_analysis_report_record(pipeline_id: str) -> dict[str, Any] | None:
    _ensure_task_store_ready()
    return task_store.load_analysis_report(pipeline_id)


def list_analysis_reports(
    limit: int = 50,
    query: str | None = None,
    min_score: float | None = None,
    min_confidence: float | None = None,
) -> list[dict[str, Any]]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return []
    return task_store.list_analysis_reports(
        limit=limit,
        query=query,
        min_score=min_score,
        min_confidence=min_confidence,
    )


def repair_analysis_report_records() -> bool:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return False
    task_store._repair_analysis_reports_from_outputs()
    return True


def save_video_record(meta: dict[str, Any]) -> bool:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return False

    video_id = str(meta.get("video_id", "")).strip()
    role = str(meta.get("role", "")).strip()
    filename = str(meta.get("filename", "")).strip()
    uploaded_at = str(meta.get("uploaded_at", "")).strip()
    video_path = str(meta.get("video_path", "")).strip()
    url = str(meta.get("url", "")).strip()
    if not all([video_id, role, filename, uploaded_at, video_path, url]):
        return False

    size_bytes = int(meta.get("size_bytes", 0))
    payload = json.dumps(meta, ensure_ascii=False)
    try:
        with task_store._lock:
            with task_store._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO video_records (
                            video_id, role, filename, uploaded_at, size_bytes, video_path, url, payload, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s::timestamptz, %s, %s, %s, %s::jsonb, NOW(), NOW())
                        ON CONFLICT (video_id)
                        DO UPDATE SET
                            role = EXCLUDED.role,
                            filename = EXCLUDED.filename,
                            uploaded_at = EXCLUDED.uploaded_at,
                            size_bytes = EXCLUDED.size_bytes,
                            video_path = EXCLUDED.video_path,
                            url = EXCLUDED.url,
                            payload = EXCLUDED.payload,
                            updated_at = NOW()
                        """,
                        (video_id, role, filename, uploaded_at, size_bytes, video_path, url, payload),
                    )
                conn.commit()
        return True
    except Exception as exc:
        logger.warning("PostgreSQL video store write failed for %s: %s", video_id, exc)
        return False


def load_video_record(video_id: str, role: str | None = None) -> dict[str, Any] | None:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return None

    try:
        with task_store._connect() as conn:
            with conn.cursor() as cur:
                if role:
                    cur.execute(
                        "SELECT payload::text FROM video_records WHERE video_id = %s AND role = %s",
                        (video_id, role),
                    )
                else:
                    cur.execute(
                        "SELECT payload::text FROM video_records WHERE video_id = %s",
                        (video_id,),
                    )
                row = cur.fetchone()
        if not row or not row[0]:
            return None
        return json.loads(row[0])
    except Exception as exc:
        logger.warning("PostgreSQL video store read failed for %s: %s", video_id, exc)
        return None


def list_video_records(role: str | None = None) -> list[dict[str, Any]]:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return []

    try:
        with task_store._connect() as conn:
            with conn.cursor() as cur:
                if role and role != "all":
                    cur.execute(
                        "SELECT payload::text FROM video_records WHERE role = %s ORDER BY uploaded_at DESC",
                        (role,),
                    )
                else:
                    cur.execute(
                        "SELECT payload::text FROM video_records ORDER BY uploaded_at DESC"
                    )
                rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            if row and row[0]:
                out.append(json.loads(row[0]))
        return out
    except Exception as exc:
        logger.warning("PostgreSQL video store list failed: %s", exc)
        return []


def delete_video_record(video_id: str, role: str | None = None) -> bool:
    _ensure_task_store_ready()
    if not task_store.is_available:
        return False

    video_id = str(video_id).strip()
    role = str(role).strip() if role else None
    if not video_id:
        return False

    try:
        with task_store._lock:
            with task_store._connect() as conn:
                with conn.cursor() as cur:
                    if role:
                        cur.execute(
                            "DELETE FROM video_records WHERE video_id = %s AND role = %s",
                            (video_id, role),
                        )
                    else:
                        cur.execute(
                            "DELETE FROM video_records WHERE video_id = %s",
                            (video_id,),
                        )
                conn.commit()
        return True
    except Exception as exc:
        logger.warning("PostgreSQL video store delete failed for %s: %s", video_id, exc)
        return False


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

    pipeline_id = str(pipeline_id).strip()
    event_type = str(event_type).strip()
    if not pipeline_id or not event_type:
        return False

    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    try:
        with task_store._lock:
            with task_store._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO pipeline_task_events (
                            pipeline_id, event_type, status, message, executor, payload, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
                        """,
                        (pipeline_id, event_type, status, message, executor, payload_json),
                    )
                conn.commit()
        return True
    except Exception as exc:
        logger.warning("PostgreSQL pipeline event write failed for %s: %s", pipeline_id, exc)
        return False



def get_pipeline_failure_stats(days: int = 30, limit: int = 20) -> dict[str, Any]:
    _ensure_task_store_ready()
    out: dict[str, Any] = {
        "window_days": max(1, int(days)),
        "total_failures": 0,
        "by_error_type": [],
        "by_executor": [],
        "recent_failures": [],
    }
    if not task_store.is_available:
        return out

    safe_days = max(1, int(days))
    safe_limit = max(1, int(limit))
    try:
        with task_store._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM pipeline_task_events
                    WHERE event_type IN ('failed', 'submit_failed')
                      AND created_at >= NOW() - (%s * INTERVAL '1 day')
                    """,
                    (safe_days,),
                )
                row = cur.fetchone()
                out["total_failures"] = int(row[0]) if row else 0

                cur.execute(
                    """
                    SELECT COALESCE(payload->>'error_type', 'unknown') AS error_type, COUNT(*) AS count
                    FROM pipeline_task_events
                    WHERE event_type IN ('failed', 'submit_failed')
                      AND created_at >= NOW() - (%s * INTERVAL '1 day')
                    GROUP BY COALESCE(payload->>'error_type', 'unknown')
                    ORDER BY count DESC, error_type ASC
                    """,
                    (safe_days,),
                )
                out["by_error_type"] = [
                    {"key": str(error_type), "count": int(count)} for error_type, count in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT COALESCE(executor, 'unknown') AS executor_name, COUNT(*) AS count
                    FROM pipeline_task_events
                    WHERE event_type IN ('failed', 'submit_failed')
                      AND created_at >= NOW() - (%s * INTERVAL '1 day')
                    GROUP BY COALESCE(executor, 'unknown')
                    ORDER BY count DESC, executor_name ASC
                    """,
                    (safe_days,),
                )
                out["by_executor"] = [
                    {"key": str(executor_name), "count": int(count)} for executor_name, count in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT
                        pipeline_id,
                        event_type,
                        status,
                        executor,
                        COALESCE(payload->>'error_type', 'unknown') AS error_type,
                        message,
                        created_at
                    FROM pipeline_task_events
                    WHERE event_type IN ('failed', 'submit_failed')
                      AND created_at >= NOW() - (%s * INTERVAL '1 day')
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (safe_days, safe_limit),
                )
                out["recent_failures"] = [
                    {
                        "pipeline_id": str(pipeline_id),
                        "event_type": str(event_type),
                        "status": str(status) if status is not None else None,
                        "executor": str(executor) if executor is not None else None,
                        "error_type": str(error_type) if error_type is not None else None,
                        "message": str(message) if message is not None else None,
                        "created_at": created_at.isoformat() if created_at is not None else None,
                    }
                    for pipeline_id, event_type, status, executor, error_type, message, created_at in cur.fetchall()
                ]
        return out
    except Exception as exc:
        logger.warning("PostgreSQL pipeline failure stats query failed: %s", exc)
        return out
