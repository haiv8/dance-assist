from __future__ import annotations

import re
from typing import Any

QUESTION_ONLY_RE = re.compile(r"^[\s?？!！。.、,，:：;；\-]+$")
MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "æ",
    "è",
    "å",
    "ç",
    "ä",
    "鍔",
    "锛",
    "銆",
    "绗",
    "璺",
    "寤",
    "搴",
    "闂",
    "",
    "�",
)


def _as_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if out == out else None


def is_usable_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or QUESTION_ONLY_RE.fullmatch(text):
        return False

    marker_hits = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
    if marker_hits >= 2:
        return False
    if marker_hits and marker_hits / max(1, len(text)) > 0.04:
        return False
    return True


def safe_text(value: Any, fallback: str | None = None) -> str | None:
    if is_usable_text(value):
        return str(value).strip()
    return fallback


def fallback_confidence_level(value: Any) -> str:
    score = _as_float(value)
    if score is None:
        return "medium"
    if score >= 0.78:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def fallback_confidence_summary(level_or_score: Any) -> str:
    level = str(level_or_score).strip().lower()
    if level not in {"high", "medium", "low"}:
        level = fallback_confidence_level(level_or_score)
    if level == "high":
        return "当前结果可信度较高，关键点跟踪、动作对齐和节奏估计整体稳定，可以作为本轮分析的主要参考。"
    if level == "low":
        return "当前结果可信度偏低，建议优先检查拍摄视角、遮挡和节奏同步情况，再结合视频回放谨慎解读。"
    return "当前结果可信度中等，整体趋势可以参考，但局部片段可能受跟踪质量或对齐稳定性影响。"


def fallback_score_summary(score: Any) -> str:
    value = _as_float(score)
    if value is None:
        return "本次分析已完成，建议结合关键片段、得分和原始视频一起复盘。"
    if value >= 80:
        return "本次动作完成度较好，可以重点保持当前节奏和动作稳定性。"
    if value >= 60:
        return "本次动作整体可参考，建议优先复盘高误差片段并做分段练习。"
    return "本次动作差异较明显，建议先从关键问题片段开始慢速分解练习。"


def fallback_overall_advice(score: Any = None) -> str:
    value = _as_float(score)
    if value is not None and value >= 80:
        return "继续保持动作节奏和身体控制，复盘时可重点打磨细节稳定性。"
    if value is not None and value < 60:
        return "建议先降低速度，围绕高误差片段逐段校正，再进行完整动作串联。"
    return "优先复盘问题片段，关注躯干稳定、关节路线和节奏一致性。"


def fallback_beginner_summary(score: Any = None, issue_count: Any = None) -> str:
    value = _as_float(score)
    count = int(issue_count) if isinstance(issue_count, int) or str(issue_count).isdigit() else None
    score_text = f"约 {value:.1f} 分" if value is not None else "已生成"
    issue_text = f"，共识别出 {count} 个重点片段" if count is not None and count > 0 else ""
    return f"本次评分{score_text}{issue_text}，建议按时间顺序逐段复盘，并先处理最明显的问题动作。"


def fallback_teaching_summary(score: Any = None, issue_count: Any = None) -> str:
    count = int(issue_count) if isinstance(issue_count, int) or str(issue_count).isdigit() else None
    issue_text = f"，优先讲评 {count} 个重点片段" if count is not None and count > 0 else ""
    return f"建议围绕动作准确性、节奏稳定性和跟踪质量进行分段讲评{issue_text}。"


def fallback_confidence_issue_copy(code: str) -> tuple[str, str]:
    if code == "tracking_coverage_low":
        return (
            "关键点覆盖率偏低，部分肢体没有被稳定识别。",
            "建议保证全身完整入镜、光照均匀，并尽量减少快速遮挡后重新分析。",
        )
    if code == "long_occlusion_gap":
        return (
            "存在较长时间的遮挡或关键点缺失。",
            "建议拉开拍摄距离，减少人与道具或身体自遮挡，确保手脚和躯干连续可见。",
        )
    if code == "alignment_unstable":
        return (
            "动作对齐稳定性不足，部分片段的匹配结果可能不够可靠。",
            "建议检查示范与学员视频的起始时刻是否接近，并尽量保留完整连续的动作片段。",
        )
    if code == "tempo_confidence_low":
        return (
            "节奏估计稳定性较低，节拍相关判断需要谨慎参考。",
            "建议使用更清晰的原始音频，或在节奏更明确的片段重新分析。",
        )
    return (
        "本轮分析存在可信度风险。",
        "建议结合原视频回放检查拍摄质量，并在条件更稳定时重新分析。",
    )


def normalized_confidence_summary(confidence: dict[str, Any] | None, fallback: Any = None) -> str:
    if isinstance(confidence, dict) and is_usable_text(confidence.get("summary")):
        return str(confidence.get("summary")).strip()
    if is_usable_text(fallback):
        return str(fallback).strip()
    if isinstance(confidence, dict):
        return fallback_confidence_summary(confidence.get("level") or confidence.get("score"))
    return fallback_confidence_summary(fallback)


def normalized_confidence_issues(confidence: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(confidence, dict):
        return []
    raw_issues = confidence.get("issues")
    if not isinstance(raw_issues, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw_issue in raw_issues:
        issue = raw_issue if isinstance(raw_issue, dict) else {}
        code = str(issue.get("code", "")).strip()
        fallback_message, fallback_suggestion = fallback_confidence_issue_copy(code)
        normalized.append(
            {
                **issue,
                "code": code,
                "message": safe_text(issue.get("message"), fallback_message),
                "suggestion": safe_text(issue.get("suggestion"), fallback_suggestion),
            }
        )
    return normalized


def marker_severity(value: Any) -> str:
    severity = str(value or "").strip().lower()
    if severity in {"severe", "clear", "high"}:
        return "high"
    if severity in {"mild", "medium"}:
        return "medium"
    return "medium"


def issue_type_text(value: Any) -> str:
    issue_type = str(value or "").strip()
    if issue_type == "pose_error":
        return "动作误差"
    if issue_type == "tempo":
        return "节奏异常"
    if issue_type == "confidence":
        return "可信度风险"
    if issue_type == "tracking_bad":
        return "跟踪问题"
    return issue_type or "待定"


def severity_text(value: Any) -> str:
    severity = str(value or "").strip().lower()
    if severity == "high":
        return "高优先级"
    if severity == "medium":
        return "中优先级"
    return "低优先级"


def time_text(sec: Any) -> str:
    value = _as_float(sec)
    if value is None:
        return "--"
    return f"{value:.2f}s"


def extract_report_issues(report: dict[str, Any]) -> list[dict[str, Any]]:
    report_payload = report.get("report") if isinstance(report.get("report"), dict) else {}
    confidence = report_payload.get("confidence") if isinstance(report_payload, dict) else {}
    pair_name = str(report.get("pair_name") or report.get("pipeline_id") or "未命名记录")
    pipeline_id = str(report.get("pipeline_id") or "")
    markers = report_payload.get("markers") if isinstance(report_payload.get("markers"), list) else []

    issues: list[dict[str, Any]] = []

    for marker in markers:
        if not isinstance(marker, dict):
            continue
        sec = _as_float(marker.get("sec"))
        if sec is None:
            continue
        severity = marker_severity(marker.get("severity"))
        issue_type = str(marker.get("type") or "pose_error")
        frame = marker.get("frame")
        issues.append(
            {
                "id": f"{pipeline_id}_marker_{frame if frame is not None else sec}_{issue_type or 'unknown'}",
                "pipeline_id": pipeline_id,
                "pair_name": pair_name,
                "teacher_video_id": report.get("teacher_video_id"),
                "user_video_id": report.get("user_video_id"),
                "type": issue_type,
                "severity": severity,
                "sec": sec,
                "frame": int(frame) if isinstance(frame, int) else None,
                "summary": f"{issue_type_text(issue_type)}，{time_text(sec)}，{severity_text(severity)}",
                "action": "建议跳回动作分析页，结合双视频和时间轴对照这一段。",
                "finished_at": report.get("finished_at") or report.get("updated_at"),
                "score_total": report.get("score_total"),
                "confidence_score": report.get("confidence_score"),
            }
        )

    tempo_segments = report_payload.get("tempo_segments") if isinstance(report_payload.get("tempo_segments"), list) else []
    for index, segment in enumerate(tempo_segments):
        if not isinstance(segment, dict):
            continue
        sec = _as_float(segment.get("start_sec", segment.get("sec", segment.get("t0"))))
        if sec is None:
            continue
        issues.append(
            {
                "id": f"{pipeline_id}_tempo_{index}",
                "pipeline_id": pipeline_id,
                "pair_name": pair_name,
                "teacher_video_id": report.get("teacher_video_id"),
                "user_video_id": report.get("user_video_id"),
                "type": "tempo",
                "severity": "medium",
                "sec": sec,
                "frame": None,
                "summary": f"第 {index + 1} 段节奏异常，建议对照拍点和动作转场。",
                "action": "可先聚焦这一段的拍点、重心转移和动作发力节奏。",
                "finished_at": report.get("finished_at") or report.get("updated_at"),
                "score_total": report.get("score_total"),
                "confidence_score": report.get("confidence_score"),
            }
        )

    confidence_summary = normalized_confidence_summary(
        confidence if isinstance(confidence, dict) else None,
        report.get("confidence_summary"),
    )
    confidence_issue_items = normalized_confidence_issues(confidence if isinstance(confidence, dict) else None)
    first_marker_sec = None
    for marker in markers:
        if isinstance(marker, dict):
            first_marker_sec = _as_float(marker.get("sec"))
            if first_marker_sec is not None:
                break

    for index, issue in enumerate(confidence_issue_items):
        issues.append(
            {
                "id": f"{pipeline_id}_confidence_{index}",
                "pipeline_id": pipeline_id,
                "pair_name": pair_name,
                "teacher_video_id": report.get("teacher_video_id"),
                "user_video_id": report.get("user_video_id"),
                "type": "confidence",
                "severity": "high",
                "sec": first_marker_sec if first_marker_sec is not None else 0.0,
                "frame": None,
                "summary": str(issue.get("message") or confidence_summary or "本轮分析存在可信度风险。"),
                "action": str(issue.get("suggestion") or "建议先改善拍摄视角或跟踪质量，再重新复测。"),
                "finished_at": report.get("finished_at") or report.get("updated_at"),
                "score_total": report.get("score_total"),
                "confidence_score": report.get("confidence_score"),
            }
        )

    issues.sort(key=lambda item: float(item.get("sec") or 0.0))
    return issues
