from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, UploadFile

from app.services.task_store import delete_video_record, load_video_record, list_video_records, save_video_record
from app.settings import settings

RoleType = Literal["teacher", "user"]
UPLOAD_CHUNK_SIZE = 1024 * 1024


def _copy_missing_files(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists():
        return
    for src in src_dir.rglob("*"):
        rel = src.relative_to(src_dir)
        dst = dst_dir / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)


def _maybe_migrate_legacy_uploads() -> None:
    if not settings.MIGRATE_LEGACY_ON_START:
        return

    marker = settings.UPLOADS_DIR / ".legacy_uploads_migrated"
    if marker.exists():
        return

    legacy_base = settings.LEGACY_UPLOADS_DIR
    if not legacy_base.exists():
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("no_legacy", encoding="utf-8")
        return

    runtime_has_data = False
    for role in ("teacher", "user"):
        role_dir = settings.UPLOADS_DIR / role
        if role_dir.exists() and any(role_dir.iterdir()):
            runtime_has_data = True
            break

    if runtime_has_data:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("runtime_has_data", encoding="utf-8")
        return

    for role in ("teacher", "user"):
        _copy_missing_files(legacy_base / role, settings.UPLOADS_DIR / role)

    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("migrated", encoding="utf-8")


def ensure_dirs() -> None:
    settings.APP_HOME.mkdir(parents=True, exist_ok=True)
    (settings.UPLOADS_DIR / "teacher").mkdir(parents=True, exist_ok=True)
    (settings.UPLOADS_DIR / "user").mkdir(parents=True, exist_ok=True)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    settings.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    _maybe_migrate_legacy_uploads()


def _safe_stem(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", text, flags=re.UNICODE)
    text = text.strip("._-")
    return text[:80] or "video"


def _extract_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in settings.ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported extension: {suffix}")
    return suffix


def _base_url(role: RoleType, filename: str) -> str:
    return f"/media/{role}/{filename}"


def _role_file_path(role: RoleType, filename: str) -> Path:
    role_dir = (settings.UPLOADS_DIR / role).resolve()
    path = (role_dir / filename).resolve()
    if path == role_dir or role_dir not in path.parents:
        raise HTTPException(status_code=400, detail="invalid video filename")
    return path


async def _write_upload_with_limit(file: UploadFile, dst: Path, max_bytes: int) -> int:
    total = 0
    try:
        with dst.open("wb") as out:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(status_code=413, detail=f"file too large, max {settings.MAX_UPLOAD_MB}MB")
                out.write(chunk)
    except Exception:
        dst.unlink(missing_ok=True)
        raise
    return total


def _normalize_video_to_mp4(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-r",
        "30",
        "-vsync",
        "cfr",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise HTTPException(status_code=500, detail=f"ffmpeg normalize failed: {r.stderr.strip()}")


def _meta_to_item(meta: dict, role: RoleType) -> dict | None:
    video_id = str(meta.get("video_id", "")).strip()
    filename = str(meta.get("filename", "")).strip()
    uploaded_at = meta.get("uploaded_at")
    size_bytes = int(meta.get("size_bytes", 0))
    if not video_id or not filename:
        return None

    try:
        video_file = _role_file_path(role, filename)
    except HTTPException:
        return None
    if not video_file.exists():
        return None

    return {
        "video_id": video_id,
        "role": role,
        "filename": filename,
        "url": _base_url(role, filename),
        "uploaded_at": uploaded_at,
        "size_bytes": size_bytes,
    }


async def save_upload(file: UploadFile, role: RoleType, name: str | None = None) -> dict:
    ensure_dirs()

    if role not in ("teacher", "user"):
        raise HTTPException(status_code=400, detail="role must be teacher or user")

    suffix = _extract_suffix(file.filename or "")
    raw_name = name if (name and name.strip()) else Path(file.filename or "video").stem
    safe_name = _safe_stem(raw_name)

    video_id = uuid.uuid4().hex[:12]
    stored_filename = f"{video_id}_{safe_name}.mp4"
    tmp_filename = f"{video_id}_{safe_name}__src{suffix}"

    role_dir = settings.UPLOADS_DIR / role
    role_dir.mkdir(parents=True, exist_ok=True)

    video_path = role_dir / stored_filename
    tmp_src_path = role_dir / tmp_filename
    max_bytes = int(settings.MAX_UPLOAD_MB) * 1024 * 1024
    written_size = await _write_upload_with_limit(file, tmp_src_path, max_bytes)
    try:
        _normalize_video_to_mp4(tmp_src_path, video_path)
    except Exception:
        video_path.unlink(missing_ok=True)
        raise
    finally:
        tmp_src_path.unlink(missing_ok=True)

    uploaded_at = datetime.now(timezone.utc)
    out_size = int(video_path.stat().st_size) if video_path.exists() else written_size
    meta = {
        "video_id": video_id,
        "role": role,
        "filename": stored_filename,
        "original_filename": file.filename,
        "size_bytes": out_size,
        "uploaded_at": uploaded_at.isoformat(),
        "video_path": str(video_path),
        "url": _base_url(role, stored_filename),
    }

    meta_path = role_dir / f"{video_id}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    save_video_record(meta)

    return {
        "video_id": video_id,
        "role": role,
        "filename": stored_filename,
        "size_bytes": out_size,
        "url": _base_url(role, stored_filename),
        "meta_url": _base_url(role, f"{video_id}.json"),
    }


def list_videos(role: Literal["teacher", "user", "all"] = "all") -> list[dict]:
    ensure_dirs()

    out: list[dict] = []
    seen_ids: set[str] = set()

    for meta in list_video_records(role):
        meta_role = str(meta.get("role", "")).strip()
        if meta_role not in ("teacher", "user"):
            continue
        item = _meta_to_item(meta, meta_role)
        if item is None:
            continue
        seen_ids.add(item["video_id"])
        out.append(item)

    roles = ["teacher", "user"] if role == "all" else [role]
    for r in roles:
        role_dir = settings.UPLOADS_DIR / r
        for meta_path in sorted(role_dir.glob("*.json")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                item = _meta_to_item(meta, r)
                if item is None or item["video_id"] in seen_ids:
                    continue
                save_video_record(meta)
                seen_ids.add(item["video_id"])
                out.append(item)
            except Exception:
                continue

    out.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
    return out


def get_video_meta(video_id: str, role: RoleType | None = None) -> dict:
    ensure_dirs()

    roles = [role] if role else ["teacher", "user"]

    for r in roles:
        meta = load_video_record(video_id, r)
        if not meta:
            continue
        item = _meta_to_item(meta, r)
        if item is None:
            continue
        meta_path = settings.UPLOADS_DIR / r / f"{video_id}.json"
        return {
            "video_id": item["video_id"],
            "role": r,
            "filename": item["filename"],
            "uploaded_at": item["uploaded_at"],
            "size_bytes": item["size_bytes"],
            "url": item["url"],
            "path": str(settings.UPLOADS_DIR / r / item["filename"]),
            "meta_path": str(meta_path),
        }

    for r in roles:
        meta_path = settings.UPLOADS_DIR / r / f"{video_id}.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            item = _meta_to_item(meta, r)
            if item is None:
                continue
            save_video_record(meta)
            return {
                "video_id": item["video_id"],
                "role": r,
                "filename": item["filename"],
                "uploaded_at": item["uploaded_at"],
                "size_bytes": item["size_bytes"],
                "url": item["url"],
                "path": str(settings.UPLOADS_DIR / r / item["filename"]),
                "meta_path": str(meta_path),
            }

    raise HTTPException(status_code=404, detail=f"video not found: {video_id}")


def _load_video_payload(video_id: str, role: RoleType | None = None) -> dict:
    meta = get_video_meta(video_id, role)
    meta_path = Path(meta["meta_path"])
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"video meta read failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="video meta payload is invalid")
    return payload


def rename_video(video_id: str, role: RoleType, name: str) -> dict:
    ensure_dirs()
    if role not in ("teacher", "user"):
        raise HTTPException(status_code=400, detail="role must be teacher or user")

    payload = _load_video_payload(video_id, role)
    safe_name = _safe_stem(name)
    if not safe_name:
        raise HTTPException(status_code=400, detail="name cannot be empty")

    old_filename = str(payload.get("filename", "")).strip()
    old_path = _role_file_path(role, old_filename)
    if not old_path.exists():
        raise HTTPException(status_code=404, detail="video file not found")

    new_filename = f"{video_id}_{safe_name}.mp4"
    new_path = old_path.with_name(new_filename)
    if old_path != new_path:
        old_path.rename(new_path)

    payload["filename"] = new_filename
    payload["video_path"] = str(new_path)
    payload["url"] = _base_url(role, new_filename)

    meta_path = settings.UPLOADS_DIR / role / f"{video_id}.json"
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_video_record(payload)

    item = _meta_to_item(payload, role)
    if item is None:
        raise HTTPException(status_code=500, detail="video rename succeeded but listing payload is invalid")
    return item


def delete_video(video_id: str, role: RoleType) -> dict:
    ensure_dirs()
    if role not in ("teacher", "user"):
        raise HTTPException(status_code=400, detail="role must be teacher or user")

    meta = get_video_meta(video_id, role)
    video_path = Path(meta["path"])
    meta_path = Path(meta["meta_path"])

    try:
        video_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"video delete failed: {exc}") from exc

    delete_video_record(video_id, role)
    return {
        "video_id": video_id,
        "role": role,
        "filename": meta["filename"],
    }
