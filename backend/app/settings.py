from __future__ import annotations

import os
from pathlib import Path


def _try_load_dotenv(project_root: Path) -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)


def _str_env(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    out = [x.strip() for x in raw.split(",") if x.strip()]
    return out or default


def _first_writable_path(candidates: list[Path]) -> Path:
    seen: set[str] = set()
    ordered: list[Path] = []
    for c in candidates:
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(c)

    for p in ordered:
        try:
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".__write_probe__"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return p
        except Exception:
            continue

    return ordered[-1]


_SETTINGS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _SETTINGS_FILE.parents[2]
_try_load_dotenv(_PROJECT_ROOT)


class Settings:
    APP_NAME: str = _str_env("DANCE_ASSIST_APP_NAME", "dance-assist-api")

    API_PREFIX: str = _str_env("DANCE_ASSIST_API_PREFIX", "/api")
    API_V1_PREFIX: str = _str_env("DANCE_ASSIST_API_V1_PREFIX", "/api/v1")
    ENABLE_V1_ROUTES: bool = _bool_env("DANCE_ASSIST_ENABLE_V1_ROUTES", True)

    ALLOWED_ORIGINS = _csv_env(
        "DANCE_ASSIST_ALLOWED_ORIGINS",
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
    )
    ALLOWED_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}
    MAX_UPLOAD_MB: int = _int_env("DANCE_ASSIST_MAX_UPLOAD_MB", 1024)

    LOG_LEVEL: str = _str_env("DANCE_ASSIST_LOG_LEVEL", "INFO")
    LOG_JSON: bool = _bool_env("DANCE_ASSIST_LOG_JSON", True)
    DATABASE_URL: str = _str_env("DANCE_ASSIST_DATABASE_URL", "")
    DATABASE_CONNECT_TIMEOUT_SEC: int = _int_env("DANCE_ASSIST_DATABASE_CONNECT_TIMEOUT_SEC", 5)
    PIPELINE_EXECUTOR: str = _str_env("DANCE_ASSIST_PIPELINE_EXECUTOR", "local_thread")
    REDIS_URL: str = _str_env("DANCE_ASSIST_REDIS_URL", "")
    REDIS_PIPELINE_QUEUE: str = _str_env("DANCE_ASSIST_REDIS_PIPELINE_QUEUE", "dance_assist:pipeline_jobs")
    REDIS_BLOCK_TIMEOUT_SEC: int = _int_env("DANCE_ASSIST_REDIS_BLOCK_TIMEOUT_SEC", 5)
    PIPELINE_MAX_RETRIES: int = _int_env("DANCE_ASSIST_PIPELINE_MAX_RETRIES", 2)
    PIPELINE_RETRY_BACKOFF_SEC: int = _int_env("DANCE_ASSIST_PIPELINE_RETRY_BACKOFF_SEC", 2)
    MIN_FREE_DISK_GB: int = _int_env("DANCE_ASSIST_MIN_FREE_DISK_GB", 2)

    BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
    PROJECT_ROOT = BASE_DIR.parent  # dance-assist/

    _LOCAL_APPDATA = os.getenv("LOCALAPPDATA")
    DEFAULT_APP_HOME = (
        Path(_LOCAL_APPDATA) / "dance-assist"
        if _LOCAL_APPDATA
        else (PROJECT_ROOT / ".runtime")
    )
    _APP_HOME_FROM_ENV = os.getenv("DANCE_ASSIST_HOME")
    APP_HOME = _first_writable_path(
        [
            Path(_APP_HOME_FROM_ENV).expanduser() if _APP_HOME_FROM_ENV else DEFAULT_APP_HOME,
            PROJECT_ROOT / ".runtime",
        ]
    )

    # Legacy locations inside repository (used for first-run migration compatibility)
    LEGACY_UPLOADS_DIR = BASE_DIR / "uploads"
    LEGACY_MODELS_DIR = PROJECT_ROOT / "models"
    LEGACY_OUTPUTS_DIR = PROJECT_ROOT / "outputs"

    # Runtime locations (recommended outside repository)
    UPLOADS_DIR = APP_HOME / "uploads"
    DATA_DIR = APP_HOME / "data"
    MODELS_DIR = APP_HOME / "models"
    OUTPUTS_DIR = APP_HOME / "outputs"

    # 0 means disabled. When >0, keep only latest N output pair folders.
    RETAIN_OUTPUT_PAIRS = _int_env("DANCE_ASSIST_RETAIN_OUTPUT_PAIRS", 0)

    # Enable one-time migration from legacy uploads by default.
    MIGRATE_LEGACY_ON_START = _bool_env("DANCE_ASSIST_MIGRATE_LEGACY_ON_START", True)


settings = Settings()
