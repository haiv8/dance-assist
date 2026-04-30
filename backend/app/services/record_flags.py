from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.settings import settings


_FLAGS_LOCK = threading.Lock()
FLAGS_PATH = settings.APP_HOME / "record_flags.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_note(value: Any) -> str:
    text = str(value or "").strip()
    return text[:500]


def _normalize_flags(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for pipeline_id, value in payload.items():
        if not isinstance(pipeline_id, str) or not pipeline_id.strip() or not isinstance(value, dict):
            continue
        out[pipeline_id] = {
            "starred": bool(value.get("starred")),
            "note": _safe_note(value.get("note")),
            "updated_at": str(value.get("updated_at") or ""),
        }
    return out


def _load_record_flags_unlocked() -> dict[str, dict[str, Any]]:
    if not FLAGS_PATH.exists():
        return {}
    try:
        payload = json.loads(FLAGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return _normalize_flags(payload)


def load_record_flags() -> dict[str, dict[str, Any]]:
    with _FLAGS_LOCK:
        return _load_record_flags_unlocked()


def _save_record_flags(flags: dict[str, dict[str, Any]]) -> None:
    FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = FLAGS_PATH.with_name(f"{FLAGS_PATH.name}.tmp")
    temp_path.write_text(json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(FLAGS_PATH)


def update_record_flags(pipeline_id: str, *, starred: bool | None = None, note: str | None = None) -> dict[str, Any]:
    safe_id = str(pipeline_id or "").strip()
    if not safe_id:
        raise ValueError("pipeline_id is required")

    with _FLAGS_LOCK:
        flags = _load_record_flags_unlocked()
        current = dict(flags.get(safe_id) or {})
        if starred is not None:
            current["starred"] = bool(starred)
        else:
            current["starred"] = bool(current.get("starred"))
        if note is not None:
            current["note"] = _safe_note(note)
        else:
            current["note"] = _safe_note(current.get("note"))
        current["updated_at"] = _utc_now()
        flags[safe_id] = current
        _save_record_flags(flags)

    return {
        "pipeline_id": safe_id,
        "starred": bool(current.get("starred")),
        "note": str(current.get("note") or ""),
        "updated_at": str(current.get("updated_at") or ""),
    }


def flag_for_record(pipeline_id: str, flags: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    safe_id = str(pipeline_id or "").strip()
    item = (flags or {}).get(safe_id) or {}
    return {
        "starred": bool(item.get("starred")),
        "user_note": _safe_note(item.get("note")),
        "flag_updated_at": str(item.get("updated_at") or "") or None,
    }
