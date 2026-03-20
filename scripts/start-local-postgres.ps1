param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$pgRoot = Join-Path $root '.runtime\pgsql\pgsql'
$pgCtl = Join-Path $pgRoot 'bin\pg_ctl.exe'
$dataDir = Join-Path $pgRoot 'data'
$logFile = Join-Path $pgRoot 'postgres.log'
if (-not (Test-Path $pgCtl)) { throw "pg_ctl not found: $pgCtl" }
& $pgCtl -D $dataDir -l $logFile -o '"-p 5432 -h 127.0.0.1"' start
