from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.services.health import collect_health_report
from app.services.task_store import initialize_task_store, list_analysis_reports, repair_analysis_report_records
from app.settings import settings

DEBUG_ARTIFACT_NAMES = {
    "debug_index.json",
    "error_curve.png",
    "tempo_curve.png",
    "top_joints.png",
    "keyframes_compare.png",
}


def _safe_dir_size(path: Path) -> int:
    if not path.exists():
        return 0

    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except Exception:
                    continue
    except Exception:
        return 0
    return total


def _safe_path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except Exception:
            return 0
    return _safe_dir_size(path)


def _storage_entry(path: Path) -> dict[str, Any]:
    size_bytes = _safe_dir_size(path)
    return {
        "path": str(path),
        "bytes": size_bytes,
        "megabytes": round(size_bytes / (1024 ** 2), 2),
    }


def _pair_dirs() -> list[Path]:
    root = settings.OUTPUTS_DIR
    if not root.exists():
        return []
    pairs = [p for p in root.iterdir() if p.is_dir()]
    pairs.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return pairs


def collect_system_status() -> dict[str, Any]:
    report = collect_health_report()
    pair_dirs = _pair_dirs()
    storage = {
        "uploads": _storage_entry(settings.UPLOADS_DIR),
        "outputs": _storage_entry(settings.OUTPUTS_DIR),
        "cache_keypoints": _storage_entry(settings.DATA_DIR / "cache_keypoints"),
        "models": _storage_entry(settings.MODELS_DIR),
        "app_home": _storage_entry(settings.APP_HOME),
    }

    return {
        "ok": report.get("ok", False),
        "checked_at": report.get("checked_at"),
        "task_store": report.get("task_store"),
        "pipeline_executor": report.get("pipeline_executor"),
        "app_home": report.get("app_home"),
        "retain_output_pairs": int(getattr(settings, "RETAIN_OUTPUT_PAIRS", 0)),
        "output_pair_count": len(pair_dirs),
        "checks": report.get("checks", {}),
        "paths": {
            "app_home": str(settings.APP_HOME),
            "uploads": str(settings.UPLOADS_DIR),
            "outputs": str(settings.OUTPUTS_DIR),
            "data": str(settings.DATA_DIR),
            "models": str(settings.MODELS_DIR),
        },
        "storage": storage,
    }


def rebuild_analysis_reports() -> dict[str, Any]:
    init_ok = initialize_task_store()
    if not init_ok:
        return {
            "ok": False,
            "action": "rebuild_analysis_reports",
            "message": "task store init failed",
            "report_count": 0,
            "affected_count": 0,
            "freed_bytes": 0,
        }

    repaired = repair_analysis_report_records()
    items = list_analysis_reports(limit=500)
    return {
        "ok": repaired,
        "action": "rebuild_analysis_reports",
        "message": "analysis reports rebuilt" if repaired else "analysis reports rebuild failed",
        "report_count": len(items),
        "affected_count": len(items),
        "freed_bytes": 0,
    }


def trim_output_pairs(keep: int | None = None) -> dict[str, Any]:
    pair_dirs = _pair_dirs()
    if keep is None:
        keep = int(getattr(settings, "RETAIN_OUTPUT_PAIRS", 0) or 5)
    keep = max(1, int(keep))

    removed = 0
    freed_bytes = 0
    for pair_dir in pair_dirs[keep:]:
        freed_bytes += _safe_path_size(pair_dir)
        shutil.rmtree(pair_dir, ignore_errors=True)
        removed += 1

    return {
        "ok": True,
        "action": "trim_output_pairs",
        "message": f"kept latest {keep} output pairs",
        "report_count": len(list_analysis_reports(limit=500)) if initialize_task_store() else None,
        "affected_count": removed,
        "freed_bytes": freed_bytes,
    }


def cleanup_debug_artifacts() -> dict[str, Any]:
    removed = 0
    freed_bytes = 0

    for pair_dir in _pair_dirs():
        debug_dir = pair_dir / "debug"
        if debug_dir.exists():
            freed_bytes += _safe_path_size(debug_dir)
            shutil.rmtree(debug_dir, ignore_errors=True)
            removed += 1

        for name in DEBUG_ARTIFACT_NAMES:
            target = pair_dir / name
            if not target.exists():
                continue
            freed_bytes += _safe_path_size(target)
            try:
                target.unlink()
                removed += 1
            except Exception:
                continue

    return {
        "ok": True,
        "action": "cleanup_debug_artifacts",
        "message": "debug artifacts removed",
        "report_count": len(list_analysis_reports(limit=500)) if initialize_task_store() else None,
        "affected_count": removed,
        "freed_bytes": freed_bytes,
    }
