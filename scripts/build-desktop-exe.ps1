param(
    [int]$ApiPort = 8000,
    [int]$WebPort = 4173
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$DistRoot = Join-Path $ProjectRoot "dist-desktop"
$BuildRoot = Join-Path $ProjectRoot "build\pyinstaller"
$IconPath = Join-Path $ProjectRoot "assets\brand\dance-assist.ico"
$PythonRoot = Split-Path (Split-Path $PythonExe -Parent) -Parent
$PythonBaseRoot = (& $PythonExe -c "import sys; print(sys.base_prefix)") | Select-Object -First 1
$LibraryBinCandidates = @(
    (Join-Path $PythonRoot "Library\bin"),
    (Join-Path $PythonBaseRoot "Library\bin")
) | Select-Object -Unique

if (-not (Test-Path $PythonExe)) {
    throw "Python not found: $PythonExe"
}

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    throw "frontend/package.json not found: $FrontendDir"
}

if (-not (Test-Path $IconPath)) {
    throw "desktop icon not found: $IconPath"
}

$binaryArgs = @()
$condaDllNames = @(
    "libssl-3-x64.dll",
    "libcrypto-3-x64.dll",
    "zlib.dll",
    "zlib1.dll",
    "libffi-8.dll",
    "ffi-8.dll",
    "libbz2.dll",
    "liblzma.dll"
)
foreach ($libraryBin in $LibraryBinCandidates) {
    if (Test-Path $libraryBin) {
        foreach ($dllName in $condaDllNames) {
            $dllPath = Join-Path $libraryBin $dllName
            if (Test-Path $dllPath) {
                $binaryArgs += @("--add-binary", "$dllPath;.")
            }
        }
    }
}

Write-Host "[1/4] Build frontend dist..."
Push-Location $FrontendDir
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
}
npm run build
if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
Pop-Location

Write-Host "[2/4] Ensure packaging dependencies..."
$hasPyInstaller = $true
try {
    & $PythonExe -m PyInstaller --version | Out-Null
} catch {
    $hasPyInstaller = $false
}

$hasPyWebView = $true
try {
    & $PythonExe -c "import webview" | Out-Null
} catch {
    $hasPyWebView = $false
}

$hasPythonNet = $true
try {
    & $PythonExe -c "import pythonnet" | Out-Null
} catch {
    $hasPythonNet = $false
}

$missingPackages = @()
if (-not $hasPyInstaller) {
    $missingPackages += "pyinstaller"
}
if (-not $hasPyWebView) {
    $missingPackages += "pywebview"
}
if (-not $hasPythonNet) {
    $missingPackages += "pythonnet"
}
if ($missingPackages.Count -gt 0) {
    & $PythonExe -m pip install @missingPackages
    if ($LASTEXITCODE -ne 0) { throw "pip install for packaging dependencies failed" }
}

Write-Host "[3/4] Build desktop exe..."
if (Test-Path $DistRoot) {
    Remove-Item -Recurse -Force $DistRoot
}
if (Test-Path $BuildRoot) {
    Remove-Item -Recurse -Force $BuildRoot
}

$pyArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--name", "dance-assist",
    "--icon", $IconPath,
    $binaryArgs,
    "--distpath", $DistRoot,
    "--workpath", $BuildRoot,
    "--specpath", $BuildRoot,
    "--add-data", "$ProjectRoot\backend;backend",
    "--add-data", "$ProjectRoot\frontend\dist;frontend\dist",
    "$ProjectRoot\desktop_launcher.py"
)

& $PythonExe @pyArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host "[4/4] Done."
Write-Host "Run: $DistRoot\dance-assist\dance-assist.exe"
Write-Host "Default URL: http://127.0.0.1:$WebPort"
Write-Host "Backend API: http://127.0.0.1:$ApiPort"
