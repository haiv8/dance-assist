param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$runtime = Join-Path $root '.runtime'
$pidDir = Join-Path $runtime 'run'
$logDir = Join-Path $runtime 'logs'
$pidFile = Join-Path $pidDir 'redis-pipeline-worker.pid'
$logFile = Join-Path $logDir 'redis-pipeline-worker.log'
$errorLogFile = Join-Path $logDir 'redis-pipeline-worker.err.log'
$python = Join-Path $root '.venv\Scripts\python.exe'
$backendDir = Join-Path $root 'backend'

New-Item -ItemType Directory -Force -Path $pidDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $python)) {
  throw "python not found: $python"
}

if (Test-Path Env:PATH) {
  Remove-Item Env:PATH -ErrorAction SilentlyContinue
}

if (Test-Path $pidFile) {
  $existingPid = (Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
  if ($existingPid) {
    $existing = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
    if ($existing) {
      Write-Output "already running: PID=$existingPid"
      exit 0
    }
  }
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$proc = Start-Process -FilePath $python -ArgumentList '-m','app.workers.pipeline_redis_worker' -WorkingDirectory $backendDir -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile -PassThru -WindowStyle Hidden
Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
Start-Sleep -Seconds 1
if ($proc.HasExited) {
  Write-Output "worker exited immediately: exit=$($proc.ExitCode)"
} else {
  Write-Output "started redis pipeline worker: PID=$($proc.Id)"
}
Write-Output "log: $logFile"
Write-Output "error log: $errorLogFile"