from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.media import _stream_with_range  # noqa: E402
from app.services import storage  # noqa: E402


class FakeUpload:
    def __init__(self, filename: str, chunks: list[bytes]) -> None:
        self.filename = filename
        self._chunks = chunks

    async def read(self, size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        if size is None or size < 0:
            data = b"".join(self._chunks)
            self._chunks.clear()
            return data
        data = self._chunks.pop(0)
        if len(data) <= size:
            return data
        self._chunks.insert(0, data[size:])
        return data[:size]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_invalid_range_is_client_error() -> None:
    with TemporaryDirectory() as tmp:
        sample = Path(tmp) / "sample.mp4"
        sample.write_bytes(b"0123456789")
        try:
            _stream_with_range(sample, "bytes=abc-def")
        except HTTPException as exc:
            assert_true(exc.status_code == 416, "invalid Range should return HTTP 416")
        else:
            raise AssertionError("invalid Range should not stream a response")


def verify_rename_ignores_tampered_video_path() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        uploads = root / "uploads"
        role_dir = uploads / "teacher"
        role_dir.mkdir(parents=True)

        video_id = "tampered1234"
        real_video = role_dir / f"{video_id}_old.mp4"
        real_video.write_bytes(b"real video")

        outside = root / "outside"
        outside.mkdir()
        outside_video = outside / "victim.mp4"
        outside_video.write_bytes(b"do not move")

        meta = {
            "video_id": video_id,
            "role": "teacher",
            "filename": real_video.name,
            "uploaded_at": "2026-05-18T00:00:00+00:00",
            "size_bytes": real_video.stat().st_size,
            "video_path": str(outside_video),
            "url": f"/media/teacher/{real_video.name}",
        }
        (role_dir / f"{video_id}.json").write_text(json.dumps(meta), encoding="utf-8")

        with patch.object(storage.settings, "UPLOADS_DIR", uploads), \
            patch.object(storage.settings, "APP_HOME", root), \
            patch.object(storage.settings, "MIGRATE_LEGACY_ON_START", False), \
            patch.object(storage, "load_video_record", return_value=None), \
            patch.object(storage, "save_video_record", return_value=True):
            renamed = storage.rename_video(video_id, "teacher", "polished")

        assert_true(outside_video.exists(), "rename should not move a path from tampered metadata")
        assert_true((role_dir / f"{video_id}_polished.mp4").exists(), "real uploaded file should be renamed")
        assert_true(renamed["filename"] == f"{video_id}_polished.mp4", "rename response should use safe filename")


def verify_lookup_continues_after_invalid_role_meta() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        uploads = root / "uploads"
        teacher_dir = uploads / "teacher"
        user_dir = uploads / "user"
        teacher_dir.mkdir(parents=True)
        user_dir.mkdir(parents=True)

        video_id = "shared1234"
        (teacher_dir / f"{video_id}.json").write_text(
            json.dumps(
                {
                    "video_id": video_id,
                    "role": "teacher",
                    "filename": "missing.mp4",
                    "uploaded_at": "2026-05-18T00:00:00+00:00",
                    "size_bytes": 0,
                }
            ),
            encoding="utf-8",
        )

        user_video = user_dir / f"{video_id}_user.mp4"
        user_video.write_bytes(b"user video")
        (user_dir / f"{video_id}.json").write_text(
            json.dumps(
                {
                    "video_id": video_id,
                    "role": "user",
                    "filename": user_video.name,
                    "uploaded_at": "2026-05-18T00:00:00+00:00",
                    "size_bytes": user_video.stat().st_size,
                    "video_path": str(user_video),
                    "url": f"/media/user/{user_video.name}",
                }
            ),
            encoding="utf-8",
        )

        with patch.object(storage.settings, "UPLOADS_DIR", uploads), \
            patch.object(storage.settings, "APP_HOME", root), \
            patch.object(storage.settings, "MIGRATE_LEGACY_ON_START", False), \
            patch.object(storage, "load_video_record", return_value=None), \
            patch.object(storage, "save_video_record", return_value=True):
            found = storage.get_video_meta(video_id)

        assert_true(found["role"] == "user", "lookup should continue after invalid metadata in another role")


def verify_failed_normalize_cleans_temp_source() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        uploads = root / "uploads"

        def fail_normalize(src: Path, dst: Path) -> None:
            raise HTTPException(status_code=500, detail="forced normalize failure")

        with patch.object(storage.settings, "UPLOADS_DIR", uploads), \
            patch.object(storage.settings, "APP_HOME", root), \
            patch.object(storage.settings, "DATA_DIR", root / "data"), \
            patch.object(storage.settings, "MODELS_DIR", root / "models"), \
            patch.object(storage.settings, "OUTPUTS_DIR", root / "outputs"), \
            patch.object(storage.settings, "MIGRATE_LEGACY_ON_START", False), \
            patch.object(storage, "_normalize_video_to_mp4", side_effect=fail_normalize):
            try:
                asyncio.run(storage.save_upload(FakeUpload("clip.mp4", [b"not a real video"]), "teacher", "clip"))
            except HTTPException as exc:
                assert_true(exc.status_code == 500, "forced normalize failure should propagate")
            else:
                raise AssertionError("normalize failure should abort upload")

        leftovers = list((uploads / "teacher").glob("*__src*"))
        assert_true(not leftovers, f"temporary upload sources should be cleaned, got {leftovers}")


def main() -> int:
    verify_invalid_range_is_client_error()
    verify_rename_ignores_tampered_video_path()
    verify_lookup_continues_after_invalid_role_meta()
    verify_failed_normalize_cleans_temp_source()
    print("media/storage hardening verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
