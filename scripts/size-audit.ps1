param(
    [int]$Top = 20
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

Write-Host "== Directory Size (Top-level) =="
Get-ChildItem -Force | ForEach-Object {
    if ($_.PSIsContainer) {
        $size = (Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    } else {
        $size = $_.Length
    }
    [PSCustomObject]@{
        Name = $_.Name
        SizeGB = [math]::Round(($size / 1GB), 3)
        SizeMB = [math]::Round(($size / 1MB), 1)
    }
} | Sort-Object SizeGB -Descending | Format-Table -AutoSize

Write-Host "`n== Largest Files =="
Get-ChildItem -Recurse -Force -File | Sort-Object Length -Descending | Select-Object -First $Top @{N='SizeGB';E={[math]::Round($_.Length/1GB,3)}}, @{N='SizeMB';E={[math]::Round($_.Length/1MB,1)}}, FullName | Format-Table -AutoSize

if (Test-Path .git) {
    Write-Host "`n== Git Object Stats =="
    git count-objects -vH
}
