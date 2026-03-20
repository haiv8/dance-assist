from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.task_store import (
    initialize_task_store,
    list_analysis_reports,
    repair_analysis_report_records,
)


def main() -> int:
    init_ok = initialize_task_store()
    if not init_ok:
        print(json.dumps({"ok": False, "message": "task store init failed"}, ensure_ascii=False))
        return 1

    repaired = repair_analysis_report_records()
    items = list_analysis_reports(limit=10)
    payload = {
        "ok": repaired,
        "count": len(items),
        "sample": items[:3],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
