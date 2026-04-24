from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


def _find_project_root() -> Path:
    start = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    for candidate in [start, *start.parents]:
        if (candidate / "desktop_launcher.py").exists() and (candidate / ".venv").exists():
            return candidate
    return start


def _log(root: Path, message: str) -> None:
    log_dir = root / ".runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with (log_dir / "desktop-entry.log").open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def main() -> int:
    root = _find_project_root()
    _log(root, f"resolved project root: {root}")
    python = root / ".venv" / "Scripts" / "python.exe"
    launcher = root / "desktop_launcher.py"
    if not python.exists() or not launcher.exists():
        _log(root, f"missing runtime: python={python} launcher={launcher}")
        return 1

    log_path = root / ".runtime" / "logs" / "desktop-launcher.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting from desktop exe launcher...\n")
        subprocess.Popen(
            [str(python), str(launcher), "--mode", "browser"],
            cwd=str(root),
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
