param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw "python not found: $python" }
Push-Location (Join-Path $root 'backend')
try {
  & $python -m app.workers.pipeline_redis_worker
}
finally {
  Pop-Location
}
