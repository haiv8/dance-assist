from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse

from app.settings import settings

router = APIRouter(tags=["media"])


def _safe_resolve(base: Path, *parts: str) -> Path:
    base_r = base.resolve()
    full = (base_r.joinpath(*parts)).resolve()
    if base_r not in full.parents and full != base_r:
        raise HTTPException(status_code=404, detail="file not found")
    return full


def _iter_file_range(path: Path, start: int, end: int, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    with path.open("rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            n = min(chunk_size, remaining)
            data = f.read(n)
            if not data:
                break
            remaining -= len(data)
            yield data


def _stream_with_range(path: Path, range_header: str | None) -> Response:
    if not path.exists() or (not path.is_file()):
        raise HTTPException(status_code=404, detail="file not found")

    file_size = int(path.stat().st_size)
    media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

    if not range_header:
        return FileResponse(
            path=str(path),
            media_type=media_type,
            headers={"Accept-Ranges": "bytes"},
        )

    # Supports a single range in form "bytes=start-end".
    if not range_header.startswith("bytes="):
        raise HTTPException(status_code=416, detail="invalid range")
    raw = range_header[len("bytes="):].strip()
    if "," in raw:
        raise HTTPException(status_code=416, detail="multiple ranges not supported")
    if "-" not in raw:
        raise HTTPException(status_code=416, detail="invalid range")

    start_s, end_s = raw.split("-", 1)
    if start_s == "":
        # suffix bytes: bytes=-500
        suffix = int(end_s)
        if suffix <= 0:
            raise HTTPException(status_code=416, detail="invalid range")
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s else (file_size - 1)
        if start > end:
            raise HTTPException(status_code=416, detail="invalid range")

    if start < 0 or start >= file_size:
        raise HTTPException(status_code=416, detail="range not satisfiable")
    end = min(end, file_size - 1)
    content_len = end - start + 1

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(content_len),
    }

    return StreamingResponse(
        _iter_file_range(path, start, end),
        status_code=206,
        media_type=media_type,
        headers=headers,
    )


@router.get("/media/{role}/{filename:path}")
def media_file(role: str, filename: str, range_header: str | None = Header(default=None, alias="Range")):
    if role not in {"teacher", "user"}:
        raise HTTPException(status_code=404, detail="file not found")
    p = _safe_resolve(settings.UPLOADS_DIR / role, filename)
    return _stream_with_range(p, range_header)


@router.get("/artifacts/{pair_name}/{filename:path}")
def artifact_file(pair_name: str, filename: str, range_header: str | None = Header(default=None, alias="Range")):
    p = _safe_resolve(settings.OUTPUTS_DIR / pair_name, filename)
    return _stream_with_range(p, range_header)

