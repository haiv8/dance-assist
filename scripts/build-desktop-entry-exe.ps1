param()

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$IconPath = Join-Path $ProjectRoot "assets\brand\dance-assist.ico"
$DistRoot = Join-Path $ProjectRoot "dist-desktop"
$DistDir = Join-Path $DistRoot "dance-assist"
$BuildRoot = Join-Path $ProjectRoot "build\pyinstaller-entry"

if (-not (Test-Path $PythonExe)) { throw "Python not found: $PythonExe" }
if (-not (Test-Path $IconPath)) { throw "Icon not found: $IconPath" }

& $PythonExe -m PyInstaller --version | Out-Null

if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Force $DistDir | Out-Null
}
if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
    New-Item -ItemType Directory -Force $DistDir | Out-Null
}
if (Test-Path $BuildRoot) {
    Remove-Item -Recurse -Force $BuildRoot
}

& $PythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name dance-assist `
    --icon $IconPath `
    --distpath $DistRoot `
    --workpath $BuildRoot `
    --specpath $BuildRoot `
    (Join-Path $ProjectRoot "desktop_entry.py")

if ($LASTEXITCODE -ne 0) { throw "Desktop entry exe build failed" }

Write-Host "Run: $DistDir\dance-assist.exe"
