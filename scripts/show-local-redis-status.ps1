param()
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$python = Join-Path $root '.venv\Scripts\python.exe'
$code = @"
try:
    import redis
    client = redis.Redis.from_url('redis://127.0.0.1:6379/0', decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
    print('running: pong=' + str(bool(client.ping())).lower())
    print('pending_jobs=' + str(int(client.llen('dance_assist:pipeline_jobs'))))
except Exception as exc:
    print(f'not_running: {exc}')
"@
$code | & $python -