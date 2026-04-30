from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class StageTimer:
    """Small helper for coarse pipeline stage timing."""

    _started_at: float = field(default_factory=time.perf_counter)
    _last_at: float = field(default_factory=time.perf_counter)
    _stages: list[dict[str, float | str]] = field(default_factory=list)

    def checkpoint(self, name: str) -> None:
        now = time.perf_counter()
        self._stages.append({
            "name": name,
            "duration_sec": round(max(0.0, now - self._last_at), 6),
        })
        self._last_at = now

    def snapshot(self) -> dict[str, object]:
        return {
            "total_sec": round(max(0.0, time.perf_counter() - self._started_at), 6),
            "stages": list(self._stages),
        }

    def snapshot_with_current_stage(self, name: str) -> dict[str, object]:
        now = time.perf_counter()
        stages = [
            *self._stages,
            {
                "name": name,
                "duration_sec": round(max(0.0, now - self._last_at), 6),
            },
        ]
        return {
            "total_sec": round(max(0.0, now - self._started_at), 6),
            "stages": stages,
        }
