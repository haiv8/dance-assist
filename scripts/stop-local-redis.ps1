param()
$ErrorActionPreference = 'Stop'
$python = Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')) '.venv\Scripts\python.exe'
$code = @"
import socket
try:
    with socket.create_connection(('127.0.0.1', 6379), timeout=2) as s:
        s.sendall(b'SHUTDOWN\r\n')
except Exception:
    pass
"@
$code | & $python -
Write-Output 'shutdown_sent'
