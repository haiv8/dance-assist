param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$EnvFile = Join-Path $ProjectRoot '.env'

function Get-DotEnvMap {
    $values = @{}
    if (-not (Test-Path $EnvFile)) {
        return $values
    }

    foreach ($raw in Get-Content -LiteralPath $EnvFile) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith('#') -or (-not $line.Contains('='))) {
            continue
        }
        $parts = $line.Split('=', 2)
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }

    return $values
}

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python not found: $PythonExe"
}

$hasUvicorn = $true
try {
    & $PythonExe -m uvicorn --version | Out-Null
} catch {
    $hasUvicorn = $false
}
if (-not $hasUvicorn) {
    Write-Host ""
    Write-Host "Backend deps are missing in virtual env:"
    Write-Host "  $PythonExe"
    Write-Host ""
    Write-Host "Please run:"
    Write-Host "  $PythonExe -m pip install -r `"$BackendDir\requirements.txt`""
    Write-Host ""
    throw "uvicorn is not installed."
}

$envMap = Get-DotEnvMap
$pipelineExecutor = if ($envMap.ContainsKey('DANCE_ASSIST_PIPELINE_EXECUTOR')) { $envMap['DANCE_ASSIST_PIPELINE_EXECUTOR'].ToLowerInvariant() } else { 'local_thread' }
$databaseUrl = if ($envMap.ContainsKey('DANCE_ASSIST_DATABASE_URL')) { $envMap['DANCE_ASSIST_DATABASE_URL'] } else { '' }
$redisUrl = if ($envMap.ContainsKey('DANCE_ASSIST_REDIS_URL')) { $envMap['DANCE_ASSIST_REDIS_URL'] } else { '' }

if ($databaseUrl -match '127\.0\.0\.1:5432' -or $databaseUrl -match 'localhost:5432') {
    Write-Host 'Ensuring local PostgreSQL is running...'
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot 'scripts\start-local-postgres.ps1')
}

if ($pipelineExecutor -eq 'redis_queue' -or $redisUrl -match '127\.0\.0\.1:6379' -or $redisUrl -match 'localhost:6379') {
    Write-Host 'Ensuring local Redis is running...'
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot 'scripts\start-local-redis.ps1')
}

if ($pipelineExecutor -eq 'redis_queue') {
    Write-Host 'Ensuring Redis pipeline worker is running...'
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot 'scripts\start-redis-pipeline-worker.ps1')
}

Write-Host "Restarting backend on $BindHost`:$Port ..."

$pids = @()
try {
    $pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
} catch {
    $pids = @()
}

foreach ($procId in $pids) {
    if ($procId -and $procId -gt 0) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Host "Stopped process PID=$procId on port $Port"
        } catch {
            Write-Warning "Failed to stop PID=${procId}: $($_.Exception.Message)"
        }
    }
}

$cmd = "`"$PythonExe`" -m uvicorn app.main:app --host $BindHost --port $Port --reload"
Start-Process powershell -WorkingDirectory $BackendDir -ArgumentList @(
    "-NoExit",
    "-Command",
    $cmd
)

Write-Host "Backend started in a new PowerShell window."