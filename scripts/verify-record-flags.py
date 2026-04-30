from __future__ import annotations

import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services import record_flags  # noqa: E402


def main() -> None:
    temp_dir = PROJECT_ROOT / ".runtime" / "temp" / "verify-record-flags"
    flags_path = temp_dir / "record_flags.json"
    original_path = record_flags.FLAGS_PATH

    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        record_flags.FLAGS_PATH = flags_path

        assert record_flags.load_record_flags() == {}, "missing flags file should load as empty dict"

        saved = record_flags.update_record_flags("test001", starred=True, note="hello")
        assert saved["starred"] is True, "starred should be saved"
        assert saved["note"] == "hello", "note should be saved"

        loaded = record_flags.load_record_flags()
        assert loaded["test001"]["starred"] is True, "saved starred should be readable"
        assert loaded["test001"]["note"] == "hello", "saved note should be readable"

        long_note = "x" * 600
        saved = record_flags.update_record_flags("test001", note=long_note)
        assert len(saved["note"]) == 500, "note should be truncated to 500 chars"

        flag = record_flags.flag_for_record("test001", record_flags.load_record_flags())
        assert flag["starred"] is True, "flag_for_record should expose starred"
        assert flag["user_note"] == "x" * 500, "flag_for_record should expose truncated note"
        assert flag["flag_updated_at"], "flag_for_record should expose flag_updated_at"

        assert record_flags.delete_record_flags("test001") is True, "existing flag should be deleted"
        assert record_flags.flag_for_record("test001", record_flags.load_record_flags())["starred"] is False
        assert record_flags.delete_record_flags("missing-id") is False, "missing flag delete should return False"
    finally:
        record_flags.FLAGS_PATH = original_path
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("record flags verification passed")


if __name__ == "__main__":
    main()
