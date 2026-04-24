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

if getattr(sys, "frozen", False):
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    for dll_dir in (bundle_dir, bundle_dir / "Library" / "bin"):
        if dll_dir.exists():
            try:
                os.add_dll_directory(str(dll_dir))
            except Exception:
                pass

import uvicorn

HOST = "127.0.0.1"
API_PORT = 8000
WEB_PORT = 4173
LOADING_ROUTE = "/__launcher__/loading"


def _launcher_loading_html() -> str:
    api_url = f"http://{HOST}:{API_PORT}/health/ready"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Dance Assist 正在启动</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #edf4f7;
      --ink: #172033;
      --muted: #647388;
      --accent: #0f8fb3;
      --accent-2: #e06f3f;
      --glass: rgba(255, 255, 255, 0.68);
      --line: rgba(23, 32, 51, 0.09);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      overflow: hidden;
      font-family: "Segoe UI Variable", "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 18% 18%, rgba(15, 143, 179, 0.18), transparent 30%),
        radial-gradient(circle at 82% 76%, rgba(224, 111, 63, 0.16), transparent 34%),
        linear-gradient(135deg, #f9fbfc 0%, var(--bg) 52%, #e8f0f4 100%);
    }}
    body::before,
    body::after {{
      content: "";
      position: fixed;
      width: 44vmax;
      height: 44vmax;
      border-radius: 999px;
      filter: blur(18px);
      opacity: 0.42;
      pointer-events: none;
    }}
    body::before {{
      left: -18vmax;
      top: -16vmax;
      background: radial-gradient(circle, rgba(15, 143, 179, 0.26), transparent 64%);
    }}
    body::after {{
      right: -16vmax;
      bottom: -18vmax;
      background: radial-gradient(circle, rgba(224, 111, 63, 0.22), transparent 62%);
    }}
    .panel {{
      position: relative;
      width: min(460px, calc(100vw - 48px));
      display: grid;
      justify-items: center;
      gap: 18px;
      padding: 42px 38px 34px;
      border-radius: 32px;
      background: var(--glass);
      border: 1px solid var(--line);
      box-shadow: 0 28px 90px rgba(23, 32, 51, 0.14);
      backdrop-filter: blur(22px);
      animation: rise 0.45s ease both;
    }}
    .mark {{
      position: relative;
      width: 92px;
      height: 92px;
      display: grid;
      place-items: center;
    }}
    .spinner {{
      position: absolute;
      inset: 0;
      border-radius: 999px;
      border: 2px solid rgba(23, 32, 51, 0.08);
      border-top-color: var(--accent);
      border-right-color: rgba(224, 111, 63, 0.72);
      animation: spin 0.96s linear infinite;
    }}
    .logo {{
      width: 58px;
      height: 58px;
      border-radius: 20px;
      object-fit: cover;
      box-shadow: 0 16px 34px rgba(15, 143, 179, 0.2);
    }}
    .brand {{
      display: grid;
      justify-items: center;
      gap: 8px;
      text-align: center;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(30px, 5vw, 42px);
      line-height: 1;
      letter-spacing: -0.055em;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
    }}
    .status {{
      min-height: 24px;
      color: var(--ink);
      font-size: 15px;
      font-weight: 700;
    }}
    .progress-line {{
      width: 100%;
      height: 6px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(23, 32, 51, 0.07);
      position: relative;
    }}
    .progress-line::after {{
      content: "";
      position: absolute;
      inset: 0;
      width: 42%;
      border-radius: inherit;
      background: linear-gradient(90deg, transparent, var(--accent), var(--accent-2), transparent);
      animation: glide 1.45s ease-in-out infinite;
    }}
    .steps {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .step-dot {{
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: rgba(23, 32, 51, 0.2);
      animation: breathe 1.8s ease-in-out infinite;
    }}
    .step-dot:nth-child(2) {{ animation-delay: 0.2s; }}
    .step-dot:nth-child(3) {{ animation-delay: 0.4s; }}
    .hint {{
      max-width: 34ch;
      text-align: center;
      font-size: 13px;
    }}
    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}
    @keyframes glide {{
      0% {{ transform: translateX(-110%); }}
      100% {{ transform: translateX(250%); }}
    }}
    @keyframes breathe {{
      0%, 100% {{ opacity: 0.32; transform: scale(0.86); }}
      50% {{ opacity: 1; transform: scale(1); }}
    }}
    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(10px) scale(0.98); }}
      to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .panel,
      .spinner,
      .progress-line::after,
      .step-dot {{
        animation: none;
      }}
    }}
  </style>
</head>
<body>
  <main class="panel">
    <div class="mark" aria-hidden="true">
      <div class="spinner"></div>
      <img class="logo" src="/dance-assist-logo.png" alt="" />
    </div>
    <div class="brand">
      <h1>Dance Assist</h1>
      <p>正在准备本地分析工作台</p>
    </div>
    <div id="status" class="status">正在启动桌面服务...</div>
    <div class="progress-line" aria-hidden="true"></div>
    <div class="steps" aria-hidden="true">
      <span class="step-dot"></span>
      <span class="step-dot"></span>
      <span class="step-dot"></span>
    </div>
    <p id="hint" class="hint">首次冷启动会稍慢一些，准备完成后会自动进入主界面。</p>
  </main>
  <script>
    const statusEl = document.getElementById('status');
    const hintEl = document.getElementById('hint');
    const apiUrl = {api_url!r};
    const appUrl = '/';
    let attempts = 0;
    const stages = [
      ['正在启动桌面服务...', '加载本地窗口与静态界面'],
      ['正在连接本地数据...', '检查 PostgreSQL 与运行目录'],
      ['正在唤醒分析队列...', '准备 Redis 与后台分析 worker'],
      ['正在检查后端状态...', '等待 API 健康检查通过']
    ];

    async function pollReady() {{
      attempts += 1;
      try {{
        const resp = await fetch(apiUrl, {{ cache: 'no-store' }});
        const data = resp.ok ? await resp.json() : null;
        if (data && data.ok) {{
          statusEl.textContent = '准备完成';
          hintEl.textContent = '正在进入 Dance Assist...';
          window.setTimeout(() => window.location.replace(appUrl), 180);
          return;
        }}
      }} catch (err) {{
        // keep waiting
      }}
      const stage = stages[Math.min(stages.length - 1, Math.floor(attempts / 4))];
      statusEl.textContent = attempts < 22 ? stage[0] : '冷启动时间稍长，请稍候...';
      hintEl.textContent = attempts < 22 ? stage[1] : '如果长时间停留，可用 run-desktop-debug.bat 查看启动日志。';
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


def _resource_dir(root: Path) -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", root)).resolve()
    return root


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
    if not start_script.exists() and getattr(sys, "frozen", False):
        for candidate in (root.parent, root.parent.parent):
            candidate_script = candidate / "scripts" / "start-local-postgres.ps1"
            if candidate_script.exists():
                start_script = candidate_script
                break
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
    if not env_file.exists() and getattr(sys, "frozen", False):
        for candidate in (root.parent, root.parent.parent):
            candidate_env = candidate / ".env"
            if candidate_env.exists():
                env_file = candidate_env
                break
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


def _wait_backend_health_report(timeout_sec: float = 25.0) -> dict | None:
    deadline = time.time() + timeout_sec
    last_report: dict | None = None
    while time.time() < deadline:
        report = _backend_health_report(timeout_sec=1.0)
        if isinstance(report, dict):
            last_report = report
            if report.get("ok"):
                return report
        time.sleep(0.5)
    return last_report


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

    redis_url = _configured_redis_url(root)
    if redis_url:
        try:
            import redis

            client = redis.Redis.from_url(redis_url, decode_responses=True)
            if client.get(_dotenv_or_env(root, "DANCE_ASSIST_REDIS_WORKER_HEARTBEAT_KEY", "dance_assist:pipeline_jobs:worker_heartbeat")):
                _log_phase("Redis pipeline worker is already alive; reusing it.")
                return None
        except Exception:
            # If Redis is still warming up, continue with the normal startup path.
            pass

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
        report = _wait_backend_health_report(timeout_sec=25.0)
        expected_home = _expected_app_home(root).resolve()
        actual_home = None
        if isinstance(report, dict) and report.get("app_home"):
            try:
                actual_home = Path(str(report["app_home"])).resolve()
            except Exception:
                actual_home = None
        if actual_home == expected_home:
            return None, None
        if not _is_port_open(HOST, API_PORT):
            _log_phase(f"Backend port {API_PORT} was released by a previous instance; starting a fresh backend.")
        else:
            _log_phase(f"Backend port {API_PORT} is occupied but not ready; waiting for it to release.")
            release_deadline = time.time() + 30.0
            while time.time() < release_deadline:
                if not _is_port_open(HOST, API_PORT):
                    _log_phase(f"Backend port {API_PORT} released; starting a fresh backend.")
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError(
                    f"Backend port {API_PORT} is already occupied by another instance, is still starting, or uses another runtime home. "
                    f"expected={expected_home} actual={actual_home or 'unknown'}"
                )

    backend_dir = _resource_dir(root) / "backend"
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
    if not _wait_port(HOST, API_PORT, timeout_sec=10):
        raise RuntimeError(f"Backend did not open port {API_PORT} in time")
    return server, thread


def _start_static_server(root: Path) -> tuple[http.server.ThreadingHTTPServer | None, threading.Thread | None]:
    if _is_port_open(HOST, WEB_PORT):
        return None, None

    dist_dir = _resource_dir(root) / "frontend" / "dist"
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
        storage_path = Path(os.getenv("DANCE_ASSIST_HOME", str(_expected_app_home(_root_dir())))) / "webview"
        storage_path.mkdir(parents=True, exist_ok=True)
        webview.create_window(
            "Dance Assist",
            url,
            width=1480,
            height=960,
            min_size=(1180, 760),
            confirm_close=True,
            background_color="#EFF3F8",
        )
        webview.start(private_mode=False, storage_path=str(storage_path))
        return True
    except Exception as exc:
        if strict:
            raise RuntimeError(f"embedded desktop window unavailable: {exc}") from exc
        print(f"[WARN] Embedded desktop window unavailable, falling back to browser: {exc}")
        return False


def _open_browser_app_window(url: str) -> bool:
    edge_candidates = [
        Path(os.getenv("ProgramFiles(x86)", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.getenv("ProgramFiles", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    edge_path = next((path for path in edge_candidates if path.exists()), None)
    if edge_path is None:
        found = shutil.which("msedge")
        edge_path = Path(found) if found else None

    if edge_path and edge_path.exists():
        subprocess.Popen(
            [
                str(edge_path),
                f"--app={url}",
                "--new-window",
                "--disable-features=Translate",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True

    webbrowser.open(url, new=2)
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

    resources: dict[str, object | None] = {
        "postgres_started": False,
        "redis_process": None,
        "redis_worker": None,
        "backend_server": None,
    }

    def _cleanup() -> None:
        if static_server is not None:
            static_server.shutdown()
            static_server.server_close()
        backend_server = resources.get("backend_server")
        if backend_server is not None:
            backend_server.should_exit = True
        redis_worker = resources.get("redis_worker")
        if redis_worker is not None:
            redis_worker.terminate()
            try:
                redis_worker.wait(timeout=5)
            except Exception:
                redis_worker.kill()
        redis_process = resources.get("redis_process")
        if redis_process is not None:
            redis_process.terminate()
            try:
                redis_process.wait(timeout=5)
            except Exception:
                redis_process.kill()
        if resources.get("postgres_started"):
            _stop_local_postgres(root)

    atexit.register(_cleanup)

    app_url = f"http://{HOST}:{WEB_PORT}"
    ready_report = _backend_health_report(timeout_sec=0.6)
    launch_url = app_url if isinstance(ready_report, dict) and ready_report.get("ok") else f"{app_url}{LOADING_ROUTE}"

    def _boot_runtime() -> None:
        try:
            _log_phase('Warming local services...')
            postgres_started, redis_process = _start_local_services(root)
            resources["postgres_started"] = postgres_started
            resources["redis_process"] = redis_process

            resources["redis_worker"] = _start_redis_pipeline_worker(root)

            _log_phase('Booting backend...')
            backend_server, _ = _start_backend(root)
            resources["backend_server"] = backend_server

            report = _wait_backend_health_report(timeout_sec=25)
            if isinstance(report, dict) and report.get("ok"):
                _log_phase(f'Dance Assist is ready: {app_url}')
            else:
                _log_phase('Backend warm-up is taking longer than expected.')
        except Exception as exc:
            _log_phase(f'Runtime boot failed: {type(exc).__name__}: {exc}')

    threading.Thread(target=_boot_runtime, daemon=True, name="dance-assist-runtime-boot").start()

    if args.mode == "browser":
        if _open_browser_app_window(launch_url):
            _log_phase('App-window browser mode started. Keep this process alive to keep services alive.')
        else:
            _log_phase('Browser mode started. Keep this process alive to keep services alive.')
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
