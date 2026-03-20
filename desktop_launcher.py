from __future__ import annotations

import argparse
import atexit
import functools
import http.server
import json
from io import BytesIO
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

try:
    import webview
except Exception:
    webview = None
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

import uvicorn

HOST = "127.0.0.1"
API_PORT = 8000
WEB_PORT = 4173
LOADING_ROUTE = "/__launcher__/loading"


def _launcher_loading_html() -> str:
    api_url = f"http://{HOST}:{API_PORT}/health"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Dance Assist is starting</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #eef3f8;
      --panel: rgba(255,255,255,0.88);
      --ink: #142033;
      --muted: #627086;
      --accent: #de6d3d;
      --accent-soft: rgba(222,109,61,0.14);
      --line: rgba(20,32,51,0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(222,109,61,0.18), transparent 34%),
        radial-gradient(circle at bottom right, rgba(20,32,51,0.10), transparent 38%),
        linear-gradient(180deg, #f6f8fb 0%, var(--bg) 100%);
    }}
    .panel {{
      width: min(560px, calc(100vw - 40px));
      padding: 30px 30px 26px;
      border-radius: 24px;
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 24px 80px rgba(20,32,51,0.12);
      backdrop-filter: blur(12px);
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}
    .dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 0 rgba(222,109,61,0.45);
      animation: pulse 1.5s infinite;
    }}
    h1 {{ margin: 20px 0 10px; font-size: 30px; line-height: 1.15; }}
    p {{ margin: 0; color: var(--muted); line-height: 1.7; }}
    .status {{ margin-top: 20px; font-size: 15px; color: var(--ink); font-weight: 600; }}
    .progress {{
      margin-top: 18px;
      width: 100%;
      height: 12px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(20,32,51,0.08);
      position: relative;
    }}
    .progress::after {{
      content: "";
      position: absolute;
      inset: 0;
      width: 38%;
      border-radius: inherit;
      background: linear-gradient(90deg, #f19a67 0%, #de6d3d 100%);
      animation: slide 1.3s ease-in-out infinite;
    }}
    .tips {{
      margin-top: 18px;
      display: grid;
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
    }}
    code {{
      font-family: Consolas, monospace;
      padding: 2px 6px;
      border-radius: 8px;
      background: rgba(20,32,51,0.06);
      color: var(--ink);
    }}
    @keyframes slide {{
      0% {{ transform: translateX(-110%); }}
      100% {{ transform: translateX(320%); }}
    }}
    @keyframes pulse {{
      0% {{ box-shadow: 0 0 0 0 rgba(222,109,61,0.45); }}
      70% {{ box-shadow: 0 0 0 10px rgba(222,109,61,0); }}
      100% {{ box-shadow: 0 0 0 0 rgba(222,109,61,0); }}
    }}
  </style>
</head>
<body>
  <main class="panel">
    <div class="eyebrow"><span class="dot"></span><span>Dance Assist launcher</span></div>
    <h1>Warming up your workspace</h1>
    <p>The desktop shell is ready. Backend services are starting in the background, and the app will open automatically as soon as the health check passes.</p>
    <div id="status" class="status">Checking backend status...</div>
    <div class="progress"></div>
    <div class="tips">
      <div>Startup path: <code>static shell -> local services -> API health check -> app</code></div>
      <div>If this page stays here for too long, check whether local PostgreSQL or Redis is still starting.</div>
    </div>
  </main>
  <script>
    const statusEl = document.getElementById('status');
    const apiUrl = {api_url!r};
    const appUrl = '/';
    let attempts = 0;

    async function pollReady() {{
      attempts += 1;
      try {{
        const resp = await fetch(apiUrl, {{ cache: 'no-store' }});
        if (resp.ok) {{
          statusEl.textContent = 'Backend is ready. Opening Dance Assist...';
          window.location.replace(appUrl);
          return;
        }}
      }} catch (err) {{
        // keep waiting
      }}
      statusEl.textContent = attempts < 6
        ? 'Starting local backend services...'
        : 'Still warming up the backend. This can take a little longer on the first launch.';
      window.setTimeout(pollReady, 800);
    }}

    pollReady();
  </script>
</body>
</html>
"""


class QuietStaticHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args):
        return

    def _normalized_path(self) -> str:
        return self.path.split('?', 1)[0].split('#', 1)[0]

    def _send_bytes(self, body: bytes, content_type: str = 'text/html; charset=utf-8'):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        return BytesIO(body)

    def send_head(self):
        if self._normalized_path() == LOADING_ROUTE:
            return self._send_bytes(_launcher_loading_html().encode('utf-8'))

        path = self.translate_path(self.path)
        requested = Path(path)
        if requested.exists() or requested.suffix:
            return super().send_head()

        index_path = Path(self.directory or '.') / 'index.html'
        if not index_path.exists():
            return super().send_head()

        self.path = '/index.html'
        return super().send_head()


def _root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _log_phase(message: str) -> None:
    stamp = time.strftime('%H:%M:%S')
    print(f'[{stamp}] {message}')


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _wait_port(host: str, port: int, timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False


def _start_local_postgres(root: Path) -> bool:
    if _is_port_open(HOST, 5432):
        return False

    start_script = root / "scripts" / "start-local-postgres.ps1"
    if not start_script.exists():
        return False

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(start_script),
    ]
    subprocess.run(cmd, check=False, capture_output=True, text=True)
    return _wait_port(HOST, 5432, timeout_sec=15)


def _stop_local_postgres(root: Path) -> None:
    pg_root = root / ".runtime" / "pgsql" / "pgsql"
    pg_ctl = pg_root / "bin" / "pg_ctl.exe"
    data_dir = pg_root / "data"
    if not pg_ctl.exists() or not data_dir.exists():
        return

    subprocess.run(
        [str(pg_ctl), "-D", str(data_dir), "stop", "-m", "fast"],
        check=False,
        capture_output=True,
        text=True,
    )


def _read_dotenv_defaults(root: Path) -> dict[str, str]:
    env_file = root / ".env"
    if not env_file.exists():
        return {}
    values: dict[str, str] = {}
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _dotenv_or_env(root: Path, key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value and value.strip():
        return value.strip()
    value = _read_dotenv_defaults(root).get(key, default)
    return value.strip() if isinstance(value, str) else default


def _configured_pipeline_executor(root: Path) -> str:
    return _dotenv_or_env(root, "DANCE_ASSIST_PIPELINE_EXECUTOR", "local_thread").lower()


def _configured_redis_url(root: Path) -> str:
    return _dotenv_or_env(root, "DANCE_ASSIST_REDIS_URL", "")


def _configured_redis_server_exe(root: Path) -> str:
    configured = _dotenv_or_env(root, "DANCE_ASSIST_REDIS_SERVER_EXE", "")
    if configured:
        return configured

    if os.name == "nt":
        default_windows = Path(r"D:\Tool\Redis-x64-3.2.100\redis-server.exe")
        if default_windows.exists():
            return str(default_windows)

    which = shutil.which("redis-server")
    return which or ""


def _should_manage_local_redis(root: Path) -> bool:
    redis_url = _configured_redis_url(root)
    if not redis_url:
        return _configured_pipeline_executor(root) == "redis_queue"

    parsed = urlparse(redis_url)
    host = (parsed.hostname or "").lower()
    port = parsed.port or 6379
    return host in {"127.0.0.1", "localhost"} and port == 6379


def _ensure_runtime_redis_conf(root: Path) -> Path:
    app_home = Path(os.getenv("DANCE_ASSIST_HOME", str(root / ".runtime")))
    redis_root = app_home / "redis"
    redis_root.mkdir(parents=True, exist_ok=True)
    data_dir = redis_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    conf_path = redis_root / "redis.conf"
    if not conf_path.exists():
        conf_path.write_text(
            "\n".join(
                [
                    "bind 127.0.0.1",
                    "protected-mode yes",
                    "port 6379",
                    f"dir {data_dir.as_posix()}",
                    "dbfilename dump.rdb",
                    'save ""',
                    "appendonly no",
                    f"logfile {(redis_root / 'redis.log').as_posix()}",
                    "loglevel notice",
                ]
            ),
            encoding="utf-8",
        )
    return conf_path


def _start_local_redis(root: Path) -> subprocess.Popen[str] | None:
    if not _should_manage_local_redis(root):
        return None
    if _is_port_open(HOST, 6379):
        return None

    redis_exe = _configured_redis_server_exe(root)
    if not redis_exe:
        bundled = root / ".runtime" / "redis" / "with-service" / "Redis-8.6.1-Windows-x64-msys2-with-Service" / "redis-server.exe"
        if bundled.exists():
            redis_exe = str(bundled)
    if not redis_exe:
        return None

    conf_path = _ensure_runtime_redis_conf(root)
    process = subprocess.Popen(
        [redis_exe, str(conf_path)],
        cwd=str(Path(redis_exe).resolve().parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if not _wait_port(HOST, 6379, timeout_sec=10):
        process.terminate()
        try:
            process.wait(timeout=5)
        except Exception:
            process.kill()
        return None
    return process


def _start_local_services(root: Path) -> tuple[bool, subprocess.Popen[str] | None]:
    results: dict[str, object] = {
        'postgres_started': False,
        'redis_process': None,
    }

    def _boot_postgres() -> None:
        results['postgres_started'] = _start_local_postgres(root)

    def _boot_redis() -> None:
        results['redis_process'] = _start_local_redis(root)

    workers = [
        threading.Thread(target=_boot_postgres, daemon=True),
        threading.Thread(target=_boot_redis, daemon=True),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    return bool(results['postgres_started']), results['redis_process'] if isinstance(results['redis_process'], subprocess.Popen) else None


def _expected_app_home(root: Path) -> Path:
    configured = _dotenv_or_env(root, "DANCE_ASSIST_HOME", "")
    if configured:
        return Path(configured)
    local_app_data = os.getenv("LOCALAPPDATA")
    return Path(local_app_data) / "dance-assist" if local_app_data else (root / ".runtime")


def _backend_health_report(timeout_sec: float = 2.0) -> dict | None:
    try:
        with urlopen(f"http://{HOST}:{API_PORT}/health/ready", timeout=timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _prepare_runtime_env(root: Path) -> None:
    # Prefer .env defaults so desktop mode uses the same runtime home as scripts and API checks.
    if not os.getenv("DANCE_ASSIST_HOME"):
        os.environ["DANCE_ASSIST_HOME"] = str(_expected_app_home(root))

    if not os.getenv("DANCE_ASSIST_RETAIN_OUTPUT_PAIRS"):
        os.environ["DANCE_ASSIST_RETAIN_OUTPUT_PAIRS"] = _dotenv_or_env(root, "DANCE_ASSIST_RETAIN_OUTPUT_PAIRS", "30") or "30"

    if not os.getenv("DANCE_ASSIST_REDIS_SERVER_EXE"):
        redis_exe = _configured_redis_server_exe(root)
        if redis_exe:
            os.environ["DANCE_ASSIST_REDIS_SERVER_EXE"] = redis_exe


def _start_redis_pipeline_worker(root: Path) -> subprocess.Popen[str] | None:
    if _configured_pipeline_executor(root) != "redis_queue":
        return None

    python = root / ".venv" / "Scripts" / "python.exe"
    backend_dir = root / "backend"
    if not python.exists() or not backend_dir.exists():
        return None

    log_dir = Path(os.getenv("DANCE_ASSIST_HOME", str(root / ".runtime"))) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "redis_pipeline_worker.log"
    handle = open(log_file, "a", encoding="utf-8")
    process = subprocess.Popen(
        [str(python), "-m", "app.workers.pipeline_redis_worker"],
        cwd=str(backend_dir),
        stdout=handle,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return process


def _start_backend(root: Path) -> tuple[uvicorn.Server | None, threading.Thread | None]:
    if _is_port_open(HOST, API_PORT):
        report = _backend_health_report()
        expected_home = _expected_app_home(root).resolve()
        actual_home = None
        if isinstance(report, dict) and report.get("app_home"):
            try:
                actual_home = Path(str(report["app_home"])).resolve()
            except Exception:
                actual_home = None
        if actual_home == expected_home:
            return None, None
        raise RuntimeError(
            f"Backend port {API_PORT} is already occupied by another instance or runtime home. "
            f"expected={expected_home} actual={actual_home or 'unknown'}"
        )

    backend_dir = root / "backend"
    if not backend_dir.exists():
        raise FileNotFoundError(f"backend dir not found: {backend_dir}")

    sys.path.insert(0, str(backend_dir))
    from app.main import app

    config = uvicorn.Config(
        app=app,
        host=HOST,
        port=API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def _start_static_server(root: Path) -> tuple[http.server.ThreadingHTTPServer | None, threading.Thread | None]:
    if _is_port_open(HOST, WEB_PORT):
        return None, None

    dist_dir = root / "frontend" / "dist"
    if not dist_dir.exists():
        raise FileNotFoundError(
            f"frontend dist not found: {dist_dir}\\n"
            "Please run: cd frontend && npm run build"
        )

    handler = functools.partial(QuietStaticHandler, directory=str(dist_dir))
    httpd = http.server.ThreadingHTTPServer((HOST, WEB_PORT), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def _open_desktop_window(url: str, *, strict: bool = False) -> bool:
    if webview is None:
        if strict:
            raise RuntimeError("pywebview is not installed in .venv")
        return False

    try:
        webview.create_window(
            "Dance Assist",
            url,
            width=1480,
            height=960,
            min_size=(1180, 760),
            confirm_close=True,
            background_color="#EFF3F8",
        )
        webview.start()
        return True
    except Exception as exc:
        if strict:
            raise RuntimeError(f"embedded desktop window unavailable: {exc}") from exc
        print(f"[WARN] Embedded desktop window unavailable, falling back to browser: {exc}")
        return False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dance Assist desktop launcher")
    parser.add_argument(
        "--mode",
        choices=["desktop", "browser", "auto"],
        default="desktop",
        help="desktop: require embedded window; browser: always open browser; auto: prefer embedded window and fall back to browser",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = _root_dir()
    _prepare_runtime_env(root)

    _log_phase('Starting desktop shell...')
    static_server, _ = _start_static_server(root)
    if not _wait_port(HOST, WEB_PORT, timeout_sec=5):
        print(f"[ERROR] Frontend shell not ready on {HOST}:{WEB_PORT}")
        return 1

    _log_phase('Warming local services...')
    postgres_started, redis_process = _start_local_services(root)
    redis_worker = _start_redis_pipeline_worker(root)

    _log_phase('Booting backend...')
    backend_server, _ = _start_backend(root)

    def _cleanup() -> None:
        if static_server is not None:
            static_server.shutdown()
            static_server.server_close()
        if backend_server is not None:
            backend_server.should_exit = True
        if redis_worker is not None:
            redis_worker.terminate()
            try:
                redis_worker.wait(timeout=5)
            except Exception:
                redis_worker.kill()
        if redis_process is not None:
            redis_process.terminate()
            try:
                redis_process.wait(timeout=5)
            except Exception:
                redis_process.kill()
        if postgres_started:
            _stop_local_postgres(root)

    atexit.register(_cleanup)

    app_url = f"http://{HOST}:{WEB_PORT}"
    launch_url = app_url if _is_port_open(HOST, API_PORT) else f"{app_url}{LOADING_ROUTE}"

    def _announce_ready() -> None:
        if _wait_port(HOST, API_PORT, timeout_sec=25):
            _log_phase(f'Dance Assist is ready: {app_url}')
        else:
            _log_phase('Backend warm-up is taking longer than expected.')

    threading.Thread(target=_announce_ready, daemon=True).start()

    if args.mode == "browser":
        webbrowser.open(launch_url, new=2)
        _log_phase('Browser mode started. Keep this window open to keep services alive.')
    elif args.mode == "desktop":
        try:
            if _open_desktop_window(launch_url, strict=True):
                _log_phase('Desktop window closed.')
                return 0
        except Exception as exc:
            print(f"[ERROR] Desktop mode requested but unavailable: {exc}")
            print("Install desktop dependencies in .venv, for example: pywebview and pythonnet.")
            return 1
    elif _open_desktop_window(launch_url, strict=False):
        _log_phase('Desktop window closed.')
        return 0
    else:
        webbrowser.open(launch_url, new=2)
        _log_phase('Embedded window unavailable. Browser mode started instead. Keep this window open.')

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Stopping...")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
