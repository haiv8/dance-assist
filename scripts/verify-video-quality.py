from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.storage import list_videos  # noqa: E402
from app.services.video_quality import check_video_pair_quality, check_video_quality  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    missing = check_video_quality("__missing_video_quality_id__")
    assert_true(missing["level"] == "error", "missing video_id should return error level")
    assert_true(missing["ok"] is False, "missing video_id should not be ok")

    teachers = list_videos("teacher")
    users = list_videos("user")
    if not teachers or not users:
        print("video quality verification skipped: no teacher/user video pair available")
        return 0

    teacher = teachers[0]
    user = users[0]
    result = check_video_pair_quality(teacher["video_id"], user["video_id"])
    assert_true(result["level"] in {"good", "warning", "error"}, "pair result should have valid level")
    assert_true(isinstance(result["checks"], list) and result["checks"], "pair result should include checks")
    assert_true(result["teacher_meta"] is not None, "teacher meta should be present")
    assert_true(result["user_meta"] is not None, "user meta should be present")
    assert_true(isinstance(result["recommendations"], list), "recommendations should be a list")

    print(
        "video quality verification passed:",
        f"level={result['level']}",
        f"checks={len(result['checks'])}",
        f"teacher={teacher['video_id']}",
        f"user={user['video_id']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
