param(
    [switch]$DryRun,
    [switch]$CleanOutputZips,
    [switch]$CleanPyCache,
    [switch]$CleanFrontendCache,
    [switch]$RunGitGc
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if (-not $CleanOutputZips -and -not $CleanPyCache -and -not $CleanFrontendCache -and -not $RunGitGc) {
    $CleanOutputZips = $true
    $CleanPyCache = $true
    $CleanFrontendCache = $true
}

$targets = @()
if ($CleanOutputZips) {
    $targets += Get-ChildItem -Recurse -File -Path "outputs" -Filter "*_outputs.zip" -ErrorAction SilentlyContinue
}
if ($CleanPyCache) {
    $targets += Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
}
if ($CleanFrontendCache) {
    if (Test-Path "frontend\.vite") { $targets += Get-Item "frontend\.vite" }
}

$targets = $targets | Sort-Object FullName -Unique
$totalBytes = ($targets | ForEach-Object {
    if ($_.PSIsContainer) {
        (Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    } else {
        $_.Length
    }
} | Measure-Object -Sum).Sum

Write-Host "Targets: $($targets.Count)"
Write-Host "Potential free space: $([math]::Round(($totalBytes / 1GB), 3)) GB"

if ($targets.Count -gt 0) {
    $targets | Select-Object FullName | Format-Table -AutoSize
}

if ($DryRun) {
    Write-Host "Dry run only. No file was deleted."
    return
}

foreach ($t in $targets) {
    Remove-Item -Recurse -Force $t.FullName -ErrorAction SilentlyContinue
}

if ($RunGitGc -and (Test-Path .git)) {
    git gc --prune=now
}

Write-Host "Cleanup finished."
