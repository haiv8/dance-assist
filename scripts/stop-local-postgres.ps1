param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$pgRoot = Join-Path $root '.runtime\pgsql\pgsql'
$pgCtl = Join-Path $pgRoot 'bin\pg_ctl.exe'
$dataDir = Join-Path $pgRoot 'data'
if (-not (Test-Path $pgCtl)) { throw "pg_ctl not found: $pgCtl" }
& $pgCtl -D $dataDir stop -m fast
