param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$pidFile = Join-Path (Join-Path $root '.runtime\run') 'redis-pipeline-worker.pid'
$logFile = Join-Path (Join-Path $root '.runtime\logs') 'redis-pipeline-worker.log'
$errorLogFile = Join-Path (Join-Path $root '.runtime\logs') 'redis-pipeline-worker.err.log'

Write-Output '=== redis pipeline worker ==='
if (-not (Test-Path $pidFile)) {
  Write-Output 'status: stopped'
  if (Test-Path $logFile) {
    Write-Output "log: $logFile"
  }
  exit 0
}

$pidValue = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
if (-not $pidValue) {
  Write-Output 'status: stale pid file'
  if (Test-Path $logFile) {
    Write-Output "log: $logFile"
  }
  if (Test-Path $errorLogFile) {
    Write-Output "error log: $errorLogFile"
  }
  exit 0
}

$proc = $null
if ($pidValue) {
  $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
}

if ($proc) {
  Write-Output 'status: running'
  Write-Output "pid: $pidValue"
  Write-Output "process: $($proc.ProcessName)"
} else {
  Write-Output 'status: stale pid file'
  Write-Output "pid: $pidValue"
}

if (Test-Path $logFile) {
  Write-Output "log: $logFile"
  Write-Output '--- last 20 log lines ---'
  Get-Content $logFile -Tail 20
}

if (Test-Path $errorLogFile) {
  Write-Output "error log: $errorLogFile"
  Write-Output '--- last 20 error log lines ---'
  Get-Content $errorLogFile -Tail 20
}