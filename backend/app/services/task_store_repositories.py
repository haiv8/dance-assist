from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable

from app.services.task_store_reports import (
    confidence_level_from_score,
    derive_confidence_from_report,
    ensure_summary_url,
    frame_analysis_rows,
    load_output_summary,
    parse_analysis_report_detail_row,
    parse_analysis_report_summary_row,
    parse_frame_analysis_range_rows,
    task_confidence_score,
    task_payload_for_storage,
    task_report_row,
    task_report_score,
)


class PipelineTaskRepository:
    def __init__(self, connect: Callable[[], Any], lock: threading.Lock, logger: logging.Logger) -> None:
        self._connect = connect
        self._lock = lock
        self._logger = logger

    def save(self, task: dict[str, Any], on_after_upsert: Callable[[Any, dict[str, Any]], None] | None = None) -> bool:
        row = self._structured_task_row(task)
        pipeline_id = row["pipeline_id"]
        if not pipeline_id:
            return False

        payload = json.dumps(task_payload_for_storage(task), ensure_ascii=False)
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
                        if on_after_upsert is not None:
                            on_after_upsert(cur, task)
                    conn.commit()
            return True
        except Exception as exc:
            self._logger.warning("PostgreSQL task store write failed for %s: %s", pipeline_id, exc)
            return False

    def load(self, pipeline_id: str) -> dict[str, Any] | None:
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
            return self._merge_task_payload(payload, structured)
        except Exception as exc:
            self._logger.warning("PostgreSQL task store read failed for %s: %s", pipeline_id, exc)
            return None

    def list_summaries(self, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        safe_limit = max(1, min(500, int(limit)))
        try:
            with self._connect() as conn:
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
                                updated_at,
                                payload::text
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
                                updated_at,
                                payload::text
                            FROM pipeline_tasks
                            ORDER BY updated_at DESC
                            LIMIT %s
                            """,
                            (safe_limit,),
                        )
                    rows = cur.fetchall()
            return [self._parse_summary_row(row) for row in rows]
        except Exception as exc:
            self._logger.warning("PostgreSQL pipeline task summary query failed: %s", exc)
            return []

    def delete(self, pipeline_id: str) -> bool:
        pipeline_id = str(pipeline_id).strip()
        if not pipeline_id:
            return False
        try:
            with self._lock:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM pipeline_tasks WHERE pipeline_id = %s", (pipeline_id,))
                    conn.commit()
            return True
        except Exception as exc:
            self._logger.warning("PostgreSQL pipeline task delete failed for %s: %s", pipeline_id, exc)
            return False

    @staticmethod
    def _structured_task_row(task: dict[str, Any]) -> dict[str, Any]:
        def as_db_text(value: Any) -> str | None:
            if value is None:
                return None
            text = str(value).strip()
            return text or None

        def as_db_float(value: Any) -> float | None:
            try:
                out = float(value)
            except Exception:
                return None
            return out if out == out else None

        def as_db_int(value: Any) -> int | None:
            try:
                return int(value)
            except Exception:
                return None

        return {
            "pipeline_id": as_db_text(task.get("pipeline_id")) or "",
            "pair_name": as_db_text(task.get("pair_name")),
            "status": as_db_text(task.get("status")),
            "stage": as_db_text(task.get("stage")),
            "progress": as_db_float(task.get("progress")),
            "teacher_video_id": as_db_text(task.get("teacher_video_id")),
            "user_video_id": as_db_text(task.get("user_video_id")),
            "executor": as_db_text(task.get("executor")),
            "attempt_count": as_db_int(task.get("attempt_count")),
            "retry_count": as_db_int(task.get("retry_count")),
            "error_type": as_db_text(task.get("error_type")),
            "queued_at": as_db_text(task.get("queued_at")),
            "started_at": as_db_text(task.get("started_at")),
            "finished_at": as_db_text(task.get("finished_at")),
            "score_total": task_report_score(task),
            "confidence_score": task_confidence_score(task),
        }

    @staticmethod
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

    @staticmethod
    def _parse_summary_row(row: tuple[Any, ...]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        raw_payload = row[17] if len(row) > 17 else None
        if raw_payload:
            try:
                loaded = json.loads(raw_payload)
            except Exception:
                loaded = {}
            if isinstance(loaded, dict):
                payload = loaded

        def as_int(value: Any) -> int | None:
            try:
                return int(value)
            except Exception:
                return None

        return {
            "pipeline_id": row[0],
            "pair_name": row[1],
            "status": row[2],
            "message": str(payload.get("message", "")).strip() or None,
            "stage": row[3],
            "progress": row[4],
            "teacher_video_id": row[5],
            "user_video_id": row[6],
            "executor": row[7],
            "attempt_count": row[8],
            "retry_count": row[9],
            "error_type": row[10],
            "error_message": str(payload.get("error_message", "")).strip() or None,
            "error_suggestion": str(payload.get("error_suggestion", "")).strip() or None,
            "raw_error": str(payload.get("raw_error", "")).strip() or None,
            "queued_at": row[11].isoformat() if row[11] is not None else None,
            "started_at": row[12].isoformat() if row[12] is not None else None,
            "finished_at": row[13].isoformat() if row[13] is not None else None,
            "score_total": row[14],
            "confidence_score": row[15],
            "updated_at": row[16].isoformat() if row[16] is not None else None,
            "cancel_requested": bool(payload.get("cancel_requested")),
            "cancel_requested_at": payload.get("cancel_requested_at"),
            "timeout_sec": as_int(payload.get("timeout_sec")),
            "timeout_at": payload.get("timeout_at"),
        }


class AnalysisReportRepository:
    def __init__(self, connect: Callable[[], Any], lock: threading.Lock, logger: logging.Logger) -> None:
        self._connect = connect
        self._lock = lock
        self._logger = logger

    def save_with_cursor(self, cur, task: dict[str, Any]) -> None:
        row = task_report_row(task)
        if not row or not row["pipeline_id"]:
            return
        cur.execute(
            """
            INSERT INTO analysis_reports (
                pipeline_id, pair_name, teacher_video_id, user_video_id, status, stage, executor,
                queued_at, started_at, finished_at, score_total, score_pose, score_tempo,
                confidence_score, confidence_level, overall_advice, confidence_summary,
                beginner_summary, teaching_summary, top_joints, files, report_payload, created_at, updated_at
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
                row["pipeline_id"], row["pair_name"], row["teacher_video_id"], row["user_video_id"], row["status"], row["stage"], row["executor"],
                row["queued_at"], row["started_at"], row["finished_at"], row["score_total"], row["score_pose"], row["score_tempo"],
                row["confidence_score"], row["confidence_level"], row["overall_advice"], row["confidence_summary"], row["beginner_summary"], row["teaching_summary"],
                json.dumps(row["top_joints"], ensure_ascii=False), json.dumps(row["files"], ensure_ascii=False), json.dumps(row["report_payload"], ensure_ascii=False),
            ),
        )
        self.save_frame_analysis_with_cursor(cur, task)

    def save_frame_analysis_with_cursor(self, cur, task: dict[str, Any]) -> None:
        pipeline_id = str(task.get("pipeline_id", "")).strip()
        rows = frame_analysis_rows(task)
        if not pipeline_id or not rows:
            return
        cur.execute("DELETE FROM pipeline_frame_analysis WHERE pipeline_id = %s", (pipeline_id,))
        cur.executemany(
            """
            INSERT INTO pipeline_frame_analysis (
                pipeline_id, frame, sec, frame_error, marker_type, severity, payload, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, NOW(), NOW())
            """,
            [(pipeline_id, row["frame"], row["sec"], row["frame_error"], row["marker_type"], row["severity"], json.dumps(row["payload"], ensure_ascii=False)) for row in rows],
        )

    def load(self, pipeline_id: str) -> dict[str, Any] | None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT pipeline_id, pair_name, teacher_video_id, user_video_id, status, stage, executor,
                               queued_at, started_at, finished_at, score_total, score_pose, score_tempo,
                               confidence_score, confidence_level, overall_advice, confidence_summary,
                               beginner_summary, teaching_summary, top_joints::text, files::text, report_payload::text,
                               created_at, updated_at
                        FROM analysis_reports
                        WHERE pipeline_id = %s
                        """,
                        (pipeline_id,),
                    )
                    row = cur.fetchone()
            return parse_analysis_report_detail_row(row) if row else None
        except Exception as exc:
            self._logger.warning("PostgreSQL analysis report read failed for %s: %s", pipeline_id, exc)
            return None

    def load_frame_range(self, pipeline_id: str, *, start_frame: int, end_frame: int) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT frame, sec, payload::text
                        FROM pipeline_frame_analysis
                        WHERE pipeline_id = %s AND frame BETWEEN %s AND %s
                        ORDER BY frame ASC
                        """,
                        (pipeline_id, start_frame, end_frame),
                    )
                    rows = cur.fetchall()
            return parse_frame_analysis_range_rows(rows)
        except Exception as exc:
            self._logger.warning("PostgreSQL frame analysis range read failed for %s: %s", pipeline_id, exc)
            return []

    def list_reports(self, *, limit: int = 50, query: str | None = None, min_score: float | None = None, min_confidence: float | None = None) -> list[dict[str, Any]]:
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
        sql = f"""
            SELECT pipeline_id, pair_name, teacher_video_id, user_video_id, status, stage, executor,
                   queued_at, started_at, finished_at, score_total, score_pose, score_tempo,
                   confidence_score, confidence_level, overall_advice, confidence_summary,
                   beginner_summary, teaching_summary, top_joints::text, files::text, updated_at
            FROM analysis_reports
            WHERE {' AND '.join(clauses)}
            ORDER BY COALESCE(finished_at, updated_at) DESC
            LIMIT %s
        """
        params.append(safe_limit)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(params))
                    rows = cur.fetchall()
            return [parse_analysis_report_summary_row(row) for row in rows]
        except Exception as exc:
            self._logger.warning("PostgreSQL analysis report query failed: %s", exc)
            return []

    def repair_from_outputs(self) -> None:
        try:
            with self._lock:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT pipeline_id, pair_name, files::text, report_payload::text
                            FROM analysis_reports
                            WHERE score_pose IS NULL OR score_tempo IS NULL OR confidence_score IS NULL
                               OR confidence_level IS NULL OR confidence_summary IS NULL OR NOT (files ? 'summary_url')
                            """
                        )
                        rows = cur.fetchall()
                        for pipeline_id, pair_name, files_text, report_text in rows:
                            summary = load_output_summary(pair_name)
                            existing_files = json.loads(files_text) if files_text else {}
                            files = ensure_summary_url(existing_files, pair_name)
                            report_payload = json.loads(report_text) if report_text else {}
                            derived_score, derived_level, derived_summary = derive_confidence_from_report(report_payload if isinstance(report_payload, dict) else {}, summary)
                            if not summary and files == existing_files and derived_score is None and derived_summary is None:
                                continue
                            def as_db_float(value: Any) -> float | None:
                                try:
                                    out = float(value)
                                except Exception:
                                    return None
                                return out if out == out else None
                            confidence_score = as_db_float(summary.get("confidence_score"))
                            if confidence_score is None:
                                confidence_score = derived_score
                            confidence_level = str(summary.get("confidence_level", "")).strip() or derived_level or confidence_level_from_score(confidence_score)
                            confidence_summary = str(summary.get("confidence_summary", "")).strip() or derived_summary or None
                            score_pose = as_db_float(summary.get("score_pose"))
                            score_tempo = as_db_float(summary.get("score_tempo"))
                            cur.execute(
                                """
                                UPDATE analysis_reports
                                SET score_pose = CASE WHEN %s IS NOT NULL THEN %s ELSE score_pose END,
                                    score_tempo = CASE WHEN %s IS NOT NULL THEN %s ELSE score_tempo END,
                                    confidence_score = CASE WHEN %s IS NOT NULL THEN %s ELSE confidence_score END,
                                    confidence_level = CASE WHEN %s::text IS NOT NULL AND %s::text <> '' THEN %s::text ELSE confidence_level END,
                                    confidence_summary = CASE WHEN %s::text IS NOT NULL AND %s::text <> '' THEN %s::text ELSE confidence_summary END,
                                    files = %s::jsonb,
                                    updated_at = NOW()
                                WHERE pipeline_id = %s
                                """,
                                (score_pose, score_pose, score_tempo, score_tempo, confidence_score, confidence_score, confidence_level, confidence_level, confidence_level, confidence_summary, confidence_summary, confidence_summary, json.dumps(files, ensure_ascii=False), pipeline_id),
                            )
                    conn.commit()
        except Exception as exc:
            self._logger.warning("PostgreSQL analysis report repair failed: %s", exc)

    def delete(self, pipeline_id: str) -> bool:
        pipeline_id = str(pipeline_id).strip()
        if not pipeline_id:
            return False
        try:
            with self._lock:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM pipeline_frame_analysis WHERE pipeline_id = %s", (pipeline_id,))
                        cur.execute("DELETE FROM analysis_reports WHERE pipeline_id = %s", (pipeline_id,))
                    conn.commit()
            return True
        except Exception as exc:
            self._logger.warning("PostgreSQL analysis report delete failed for %s: %s", pipeline_id, exc)
            return False


class VideoRecordRepository:
    def __init__(self, connect: Callable[[], Any], lock: threading.Lock, logger: logging.Logger) -> None:
        self._connect = connect
        self._lock = lock
        self._logger = logger

    def save(self, meta: dict[str, Any]) -> bool:
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
            with self._lock:
                with self._connect() as conn:
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
            self._logger.warning("PostgreSQL video store write failed for %s: %s", video_id, exc)
            return False

    def load(self, video_id: str, role: str | None = None) -> dict[str, Any] | None:
        try:
            with self._connect() as conn:
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
            self._logger.warning("PostgreSQL video store read failed for %s: %s", video_id, exc)
            return None

    def list(self, role: str | None = None) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    if role and role != "all":
                        cur.execute(
                            "SELECT payload::text FROM video_records WHERE role = %s ORDER BY uploaded_at DESC",
                            (role,),
                        )
                    else:
                        cur.execute("SELECT payload::text FROM video_records ORDER BY uploaded_at DESC")
                    rows = cur.fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                if row and row[0]:
                    out.append(json.loads(row[0]))
            return out
        except Exception as exc:
            self._logger.warning("PostgreSQL video store list failed: %s", exc)
            return []

    def delete(self, video_id: str, role: str | None = None) -> bool:
        video_id = str(video_id).strip()
        role = str(role).strip() if role else None
        if not video_id:
            return False

        try:
            with self._lock:
                with self._connect() as conn:
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
            self._logger.warning("PostgreSQL video store delete failed for %s: %s", video_id, exc)
            return False


class PipelineEventRepository:
    def __init__(self, connect: Callable[[], Any], lock: threading.Lock, logger: logging.Logger) -> None:
        self._connect = connect
        self._lock = lock
        self._logger = logger

    def save(
        self,
        pipeline_id: str,
        event_type: str,
        *,
        status: str | None = None,
        message: str | None = None,
        executor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        pipeline_id = str(pipeline_id).strip()
        event_type = str(event_type).strip()
        if not pipeline_id or not event_type:
            return False

        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        try:
            with self._lock:
                with self._connect() as conn:
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
            self._logger.warning("PostgreSQL pipeline event write failed for %s: %s", pipeline_id, exc)
            return False

    def failure_stats(self, days: int = 30, limit: int = 20) -> dict[str, Any]:
        out: dict[str, Any] = {
            "window_days": max(1, int(days)),
            "total_failures": 0,
            "by_error_type": [],
            "by_executor": [],
            "recent_failures": [],
        }
        safe_days = max(1, int(days))
        safe_limit = max(1, int(limit))
        try:
            with self._connect() as conn:
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
            self._logger.warning("PostgreSQL pipeline failure stats query failed: %s", exc)
            return out

    def delete(self, pipeline_id: str) -> bool:
        pipeline_id = str(pipeline_id).strip()
        if not pipeline_id:
            return False
        try:
            with self._lock:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM pipeline_task_events WHERE pipeline_id = %s", (pipeline_id,))
                    conn.commit()
            return True
        except Exception as exc:
            self._logger.warning("PostgreSQL pipeline event delete failed for %s: %s", pipeline_id, exc)
            return False
