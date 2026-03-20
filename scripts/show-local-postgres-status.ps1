param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$psql = Join-Path $root '.runtime\pgsql\pgsql\bin\psql.exe'
if (-not (Test-Path $psql)) { throw "psql not found: $psql" }
if (-not $env:PGPASSWORD) { $env:PGPASSWORD = 'DanceAssist_pg_2026!' }

Write-Host '== PostgreSQL Connection ==' -ForegroundColor Cyan
& $psql -h 127.0.0.1 -p 5432 -U postgres -d dance_assist -tAc "SELECT current_database() || '|' || current_user;"

Write-Host ''
Write-Host '== Tables ==' -ForegroundColor Cyan
& $psql -h 127.0.0.1 -p 5432 -U postgres -d dance_assist -c "\dt"

Write-Host ''
Write-Host '== Counts ==' -ForegroundColor Cyan
& $psql -h 127.0.0.1 -p 5432 -U postgres -d dance_assist -tAc "SELECT 'video_records=' || count(*) FROM video_records; SELECT 'pipeline_tasks=' || count(*) FROM pipeline_tasks; SELECT 'pipeline_task_events=' || count(*) FROM pipeline_task_events;"

Write-Host ''
Write-Host '== Latest Pipeline Tasks ==' -ForegroundColor Cyan
& $psql -h 127.0.0.1 -p 5432 -U postgres -d dance_assist -c "SELECT pipeline_id, payload->>'status' AS status, payload->>'pair_name' AS pair_name, updated_at FROM pipeline_tasks ORDER BY updated_at DESC LIMIT 10;"

Write-Host ''
Write-Host '== Video Records ==' -ForegroundColor Cyan
& $psql -h 127.0.0.1 -p 5432 -U postgres -d dance_assist -c "SELECT video_id, role, filename, uploaded_at FROM video_records ORDER BY uploaded_at DESC LIMIT 10;"

Write-Host ''
Write-Host '== Latest Pipeline Events ==' -ForegroundColor Cyan
& $psql -h 127.0.0.1 -p 5432 -U postgres -d dance_assist -c "SELECT pipeline_id, event_type, status, executor, created_at FROM pipeline_task_events ORDER BY created_at DESC LIMIT 20;"
