param()
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$runtimeRedisRoot = Join-Path $root '.runtime\redis'
$runtimeRedisDataDir = Join-Path $runtimeRedisRoot 'data'
$runtimeRedisLogFile = Join-Path $runtimeRedisRoot 'redis.log'
$runtimeRedisConf = Join-Path $runtimeRedisRoot 'redis.conf'

function Get-DotEnvValue([string]$name) {
  $envFile = Join-Path $root '.env'
  if (-not (Test-Path $envFile)) {
    return $null
  }

  foreach ($raw in Get-Content -LiteralPath $envFile) {
    $line = $raw.Trim()
    if (-not $line -or $line.StartsWith('#') -or (-not $line.Contains('='))) {
      continue
    }
    $parts = $line.Split('=', 2)
    if ($parts[0].Trim() -eq $name) {
      return $parts[1].Trim()
    }
  }

  return $null
}

$externalRedisExe = if ($env:DANCE_ASSIST_REDIS_SERVER_EXE) {
  $env:DANCE_ASSIST_REDIS_SERVER_EXE
} else {
  $fromDotEnv = Get-DotEnvValue 'DANCE_ASSIST_REDIS_SERVER_EXE'
  if ($fromDotEnv) { $fromDotEnv } else { 'D:\Tool\Redis-x64-3.2.100\redis-server.exe' }
}
$bundledRedisRoot = Join-Path $root '.runtime\redis\with-service\Redis-8.6.1-Windows-x64-msys2-with-Service'
$bundledRedisExe = Join-Path $bundledRedisRoot 'RedisService.exe'

function Test-RedisListening {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect('127.0.0.1', 6379, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(500)
    $client.Close()
    return $ok
  } catch {
    return $false
  }
}

function Ensure-RuntimeRedisConfig {
  New-Item -ItemType Directory -Force -Path $runtimeRedisRoot | Out-Null
  New-Item -ItemType Directory -Force -Path $runtimeRedisDataDir | Out-Null
  if (Test-Path $runtimeRedisConf) {
    return
  }

  @"
bind 127.0.0.1
protected-mode yes
port 6379
dir $($runtimeRedisDataDir -replace '\\', '/')
dbfilename dump.rdb
save ""
appendonly no
logfile $($runtimeRedisLogFile -replace '\\', '/')
loglevel notice
"@ | Set-Content -LiteralPath $runtimeRedisConf -Encoding ascii
}

if (Test-RedisListening) {
  Write-Output 'already_running'
  exit 0
}

Ensure-RuntimeRedisConfig

if (Test-Path $externalRedisExe) {
  Start-Process -FilePath $externalRedisExe -ArgumentList @($runtimeRedisConf) -WorkingDirectory (Split-Path -Parent $externalRedisExe) -WindowStyle Hidden | Out-Null
  Write-Output "started_external:$externalRedisExe"
  exit 0
}

if (-not (Test-Path $bundledRedisExe)) {
  throw "Redis executable not found. Checked: $externalRedisExe ; $bundledRedisExe"
}

Start-Process -FilePath $bundledRedisExe -ArgumentList @('run', '--foreground', '-c', 'redis-local.conf') -WorkingDirectory $bundledRedisRoot -WindowStyle Hidden | Out-Null
Write-Output 'started_bundled'