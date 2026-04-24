from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException

from app.settings import settings


COACH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "priority_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "time_hint": {"type": ["string", "null"]},
                    "reason": {"type": "string"},
                    "practice_tip": {"type": "string"},
                },
                "required": ["title", "severity", "time_hint", "reason", "practice_tip"],
            },
        },
        "practice_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "duration_min": {"type": "integer"},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "success_criteria": {"type": "string"},
                },
                "required": ["title", "duration_min", "steps", "success_criteria"],
            },
        },
        "teacher_notes": {"type": "array", "items": {"type": "string"}},
        "safety_note": {"type": ["string", "null"]},
    },
    "required": ["summary", "priority_issues", "practice_plan", "teacher_notes", "safety_note"],
}


def _score_text(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "暂无"


def _time_hint(issue: dict[str, Any]) -> str | None:
    try:
        return f"{float(issue.get('sec')):.2f}s"
    except Exception:
        return None


def _compact_report(summary: dict[str, Any]) -> dict[str, Any]:
    report = summary.get("report") if isinstance(summary.get("report"), dict) else {}
    confidence = report.get("confidence") if isinstance(report.get("confidence"), dict) else {}
    recommendations = report.get("recommendations") if isinstance(report.get("recommendations"), dict) else {}
    beginner_report = report.get("beginner_report") if isinstance(report.get("beginner_report"), dict) else {}
    teaching_report = report.get("teaching_report") if isinstance(report.get("teaching_report"), dict) else {}
    scores = report.get("scores") if isinstance(report.get("scores"), dict) else {}
    issues = summary.get("issues") if isinstance(summary.get("issues"), list) else []

    return {
        "pipeline_id": summary.get("pipeline_id"),
        "pair_name": summary.get("pair_name"),
        "status": summary.get("status"),
        "score_total": report.get("score_0_100") or scores.get("score_total"),
        "score_pose": scores.get("score_pose"),
        "score_tempo": scores.get("score_tempo"),
        "confidence_score": confidence.get("score"),
        "confidence_level": confidence.get("level"),
        "confidence_summary": confidence.get("summary"),
        "overall_advice": recommendations.get("overall"),
        "beginner_summary": beginner_report.get("summary"),
        "teaching_summary": teaching_report.get("summary"),
        "top_joints": report.get("top_joints") if isinstance(report.get("top_joints"), list) else [],
        "issues": [
            {
                "type": issue.get("type"),
                "severity": issue.get("severity"),
                "sec": issue.get("sec"),
                "summary": issue.get("summary"),
                "action": issue.get("action"),
            }
            for issue in issues[:6]
            if isinstance(issue, dict)
        ],
    }


def _local_coach(summary: dict[str, Any], *, setup_hint: str | None = None) -> dict[str, Any]:
    compact = _compact_report(summary)
    issues = compact["issues"]
    score = compact.get("score_total")
    score_copy = _score_text(score)
    key_issues = issues[:3]

    priority_issues = []
    for issue in key_issues:
        priority_issues.append(
            {
                "title": str(issue.get("summary") or "重点动作片段"),
                "severity": issue.get("severity") if issue.get("severity") in {"high", "medium", "low"} else "medium",
                "time_hint": _time_hint(issue),
                "reason": str(issue.get("action") or "该片段对整体动作完成度和复盘效率影响较大。"),
                "practice_tip": "先慢速分解 3 次，再按原速跟练 2 次，最后对照示范视频检查动作路线。",
            }
        )

    if not priority_issues:
        priority_issues.append(
            {
                "title": "先复盘整体动作稳定性",
                "severity": "medium",
                "time_hint": None,
                "reason": "当前报告没有明确问题片段，适合先从整体节奏和动作完整度入手。",
                "practice_tip": "完整跟练一遍后，重点观察起势、转场和收势是否稳定。",
            }
        )

    return {
        "pipeline_id": str(summary.get("pipeline_id") or ""),
        "pair_name": summary.get("pair_name"),
        "generated_by": "local_fallback",
        "model": None,
        "summary": (
            f"本次动作评分为 {score_copy} 分。建议先处理高优先级问题片段，再回到完整动作串联，"
            "不要一次性修改太多细节。"
        ),
        "priority_issues": priority_issues,
        "practice_plan": [
            {
                "title": "问题片段慢速拆解",
                "duration_min": 8,
                "steps": ["定位第一个重点片段", "按 0.75 倍速模仿示范", "记录最容易偏移的关节或节奏点"],
                "success_criteria": "能够连续 2 次完成该片段，并且动作路线与示范更接近。",
            },
            {
                "title": "完整动作串联",
                "duration_min": 6,
                "steps": ["从片段前 3 秒开始练", "恢复原速", "完成后立刻回看对照舞台"],
                "success_criteria": "完整动作不断拍，且重点片段不再明显拖慢或变形。",
            },
        ],
        "teacher_notes": [
            compact.get("confidence_summary") or "复盘时需要结合可信度判断，不要只看总分。",
            "讲评顺序建议是：节奏是否对齐、身体重心是否稳定、关键关节路线是否清晰。",
        ],
        "safety_note": "AI建议只作为训练辅助，疼痛、受伤或高强度动作请以专业老师现场指导为准。",
        "setup_hint": setup_hint,
    }


def _extract_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts).strip()


def _call_openai(compact: dict[str, Any]) -> dict[str, Any]:
    body = {
        "model": settings.OPENAI_MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "你是一个专业、克制、鼓励型的舞蹈训练助教。"
                    "只能基于输入的评分、问题片段、可信度和报告摘要给建议。"
                    "不要编造不存在的视频细节，不要做医疗诊断。"
                    "输出必须是中文 JSON，并严格匹配给定 schema。"
                ),
            },
            {
                "role": "user",
                "content": "请把这份舞蹈动作分析结果转成可执行训练建议：\n"
                + json.dumps(compact, ensure_ascii=False),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "dance_ai_coach",
                "strict": True,
                "schema": COACH_SCHEMA,
            }
        },
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    url = settings.OPENAI_BASE_URL.rstrip("/") + "/responses"
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.ALIYUN_TIMEOUT_SEC) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {detail[:500]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {type(exc).__name__}: {exc}") from exc

    payload = json.loads(raw)
    output_text = _extract_output_text(payload)
    if not output_text:
        raise HTTPException(status_code=502, detail="OpenAI response did not include output_text")
    return _normalize_coach_payload(json.loads(output_text))


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""


def _parse_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        stripped = stripped[start : end + 1]
    return json.loads(stripped)


def _normalize_coach_payload(value: dict[str, Any]) -> dict[str, Any]:
    out = value if isinstance(value, dict) else {}
    out["summary"] = str(out.get("summary") or "已生成本次训练建议。")

    priority_issues = out.get("priority_issues")
    out["priority_issues"] = priority_issues if isinstance(priority_issues, list) else []
    for item in out["priority_issues"]:
        if not isinstance(item, dict):
            continue
        if item.get("severity") not in {"high", "medium", "low"}:
            item["severity"] = "medium"
        item["title"] = str(item.get("title") or "重点问题")
        item["reason"] = str(item.get("reason") or "该片段需要优先复盘。")
        item["practice_tip"] = str(item.get("practice_tip") or "建议慢速分解后再原速串联。")
        item["time_hint"] = None if item.get("time_hint") is None else str(item.get("time_hint"))

    practice_plan = out.get("practice_plan")
    out["practice_plan"] = practice_plan if isinstance(practice_plan, list) else []
    for item in out["practice_plan"]:
        if not isinstance(item, dict):
            continue
        item["title"] = str(item.get("title") or "专项练习")
        try:
            item["duration_min"] = int(item.get("duration_min") or 5)
        except Exception:
            item["duration_min"] = 5
        steps = item.get("steps")
        item["steps"] = [str(step) for step in steps] if isinstance(steps, list) else []
        item["success_criteria"] = str(item.get("success_criteria") or "动作能稳定完成且节奏不明显失衡。")

    teacher_notes = out.get("teacher_notes")
    if isinstance(teacher_notes, list):
        out["teacher_notes"] = [str(item) for item in teacher_notes]
    elif teacher_notes:
        out["teacher_notes"] = [str(teacher_notes)]
    else:
        out["teacher_notes"] = []

    safety_note = out.get("safety_note")
    out["safety_note"] = None if safety_note is None else str(safety_note)
    return out


def _call_aliyun(compact: dict[str, Any]) -> dict[str, Any]:
    body = {
        "model": settings.ALIYUN_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个专业、克制、鼓励型的舞蹈训练助教。"
                    "只能基于输入的评分、问题片段、可信度和报告摘要给建议。"
                    "不要编造不存在的视频细节，不要做医疗诊断。"
                    "只输出一个 JSON 对象，不要输出 Markdown。"
                    "JSON 字段必须包含 summary、priority_issues、practice_plan、teacher_notes、safety_note。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请把这份舞蹈动作分析结果转成可执行训练建议。"
                    "请控制在 300 字以内，priority_issues 最多 3 项，practice_plan 最多 2 项。"
                    "priority_issues 每项字段：title、severity(high/medium/low)、time_hint、reason、practice_tip。"
                    "practice_plan 每项字段：title、duration_min、steps、success_criteria。\n"
                    + json.dumps(compact, ensure_ascii=False)
                ),
            },
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    url = settings.ALIYUN_BASE_URL.rstrip("/") + "/chat/completions"
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.ALIYUN_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.OPENAI_TIMEOUT_SEC) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Aliyun DashScope request failed: {detail[:500]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Aliyun DashScope request failed: {type(exc).__name__}: {exc}") from exc

    payload = json.loads(raw)
    content = _extract_chat_content(payload)
    if not content:
        raise HTTPException(status_code=502, detail="Aliyun DashScope response did not include message content")
    return _normalize_coach_payload(_parse_json_text(content))


def ai_provider_status() -> dict[str, Any]:
    provider = str(settings.AI_PROVIDER or "aliyun").strip().lower()
    if provider == "openai":
        return {
            "provider": "openai",
            "configured": bool(settings.OPENAI_API_KEY),
            "model": settings.OPENAI_MODEL,
            "base_url": settings.OPENAI_BASE_URL,
        }
    if provider == "local":
        return {
            "provider": "local",
            "configured": True,
            "model": None,
            "base_url": None,
        }
    return {
        "provider": "aliyun",
        "configured": bool(settings.ALIYUN_API_KEY),
        "model": settings.ALIYUN_MODEL,
        "base_url": settings.ALIYUN_BASE_URL,
    }


def generate_ai_coach(summary: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(summary, dict) or not summary.get("pipeline_id"):
        raise HTTPException(status_code=404, detail="pipeline summary not found")

    compact = _compact_report(summary)
    provider = str(settings.AI_PROVIDER or "aliyun").strip().lower()

    if provider == "local":
        return _local_coach(summary, setup_hint="当前 AI_PROVIDER=local，正在使用本地规则版助教建议。")

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            return _local_coach(summary, setup_hint="设置 OPENAI_API_KEY 或 DANCE_ASSIST_OPENAI_API_KEY 后会启用 OpenAI 助教。")
        try:
            coach = _call_openai(compact)
            return {
                "pipeline_id": str(summary.get("pipeline_id") or ""),
                "pair_name": summary.get("pair_name"),
                "generated_by": "openai",
                "model": settings.OPENAI_MODEL,
                "setup_hint": None,
                **coach,
            }
        except HTTPException as exc:
            return _local_coach(summary, setup_hint=f"OpenAI 暂不可用，已使用本地建议兜底：{str(exc.detail)[:160]}")

    if not settings.ALIYUN_API_KEY:
        return _local_coach(summary, setup_hint="设置 DASHSCOPE_API_KEY 或 DANCE_ASSIST_ALIYUN_API_KEY 后会启用阿里云百炼 AI 助教。")
    try:
        coach = _call_aliyun(compact)
        return {
            "pipeline_id": str(summary.get("pipeline_id") or ""),
            "pair_name": summary.get("pair_name"),
            "generated_by": "aliyun",
            "model": settings.ALIYUN_MODEL,
            "setup_hint": None,
            **coach,
        }
    except HTTPException as exc:
        return _local_coach(summary, setup_hint=f"阿里云百炼暂不可用，已使用本地建议兜底：{str(exc.detail)[:160]}")
