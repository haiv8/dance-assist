param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$runtime = Join-Path $root '.runtime'
$pidDir = Join-Path $runtime 'run'
$logDir = Join-Path $runtime 'logs'
$pidFile = Join-Path $pidDir 'redis-pipeline-worker.pid'
$logFile = Join-Path $logDir 'redis-pipeline-worker.log'
$errorLogFile = Join-Path $logDir 'redis-pipeline-worker.err.log'
$workerScript = Join-Path $root 'scripts\run-redis-pipeline-worker.ps1'

New-Item -ItemType Directory -Force -Path $pidDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

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

$processPath = [System.Environment]::GetEnvironmentVariable('Path', 'Process')
$processPATH = [System.Environment]::GetEnvironmentVariable('PATH', 'Process')
if ($processPath -and $processPATH) {
  [System.Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
}

$proc = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$workerScript -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile -PassThru -WindowStyle Hidden
Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
Start-Sleep -Seconds 1
if ($proc.HasExited) {
  Write-Output "worker exited immediately: exit=$($proc.ExitCode)"
} else {
  Write-Output "started redis pipeline worker: PID=$($proc.Id)"
}
Write-Output "log: $logFile"
Write-Output "error log: $errorLogFile"