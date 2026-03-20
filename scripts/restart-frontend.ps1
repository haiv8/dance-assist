param(
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendDir = Join-Path $ProjectRoot "frontend"

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    Write-Error "frontend/package.json not found: $FrontendDir"
}

Write-Host "Restarting frontend on port $Port ..."

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

Start-Process powershell -WorkingDirectory $FrontendDir -ArgumentList @(
    "-NoExit",
    "-Command",
    "npm run dev"
)

Write-Host "Frontend started in a new PowerShell window."
