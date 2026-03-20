param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$pidFile = Join-Path (Join-Path $root '.runtime\run') 'redis-pipeline-worker.pid'

if (-not (Test-Path $pidFile)) {
  Write-Output 'worker not running (no pid file)'
  exit 0
}

$pidValue = (Get-Content $pidFile | Select-Object -First 1).Trim()
if (-not $pidValue) {
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  Write-Output 'worker not running (empty pid file)'
  exit 0
}

$proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
if ($proc) {
  Stop-Process -Id $proc.Id -Force
  Write-Output "stopped redis pipeline worker: PID=$pidValue"
} else {
  Write-Output "worker process not found: PID=$pidValue"
}
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
