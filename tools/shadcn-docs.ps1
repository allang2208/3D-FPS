<#
shadcn/ui docs site one-click start/stop (local deploy, E:\3d\shadcn-ui)

Usage:
  powershell -ExecutionPolicy Bypass -File tools/shadcn-docs.ps1                        # start (http://localhost:4000)
  powershell -ExecutionPolicy Bypass -File tools/shadcn-docs.ps1 -Stop                 # stop
  powershell -ExecutionPolicy Bypass -File tools/shadcn-docs.ps1 -HostName 0.0.0.0     # LAN access
  powershell -ExecutionPolicy Bypass -File tools/shadcn-docs.ps1 -Port 4001            # custom port

Why: official dev script `pnpm icons:dev & next dev` uses Unix `&` semantics.
On Windows cmd it runs sequentially and icons:dev never exits (watch), so next never starts.
This script starts both processes separately and checks deps/build first.
#>
param(
  [string]$DocDir = 'E:\3d\shadcn-ui',
  [int]$Port = 4000,
  [string]$HostName = 'localhost',
  [switch]$Stop
)

$ErrorActionPreference = 'Stop'
$PidsFile = Join-Path $DocDir '.shadcn-docs.pids'
$V4Dir = Join-Path $DocDir 'apps\v4'

function Log([string]$m) { Write-Host "[shadcn-docs] $m" }

function Stop-Tree([int]$procId) {
  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ParentProcessId -eq $procId } |
    ForEach-Object { Stop-Tree $_.ProcessId }
  Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

function Test-Url([string]$url) {
  try { $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5; return ($r.StatusCode -eq 200) } catch { return $false }
}

if ($Stop) {
  if (Test-Path $PidsFile) {
    Get-Content $PidsFile | ForEach-Object {
      $parts = $_ -split '\|'
      if ($parts.Count -eq 2) {
        Log ("stopping " + $parts[0] + " (PID " + $parts[1] + ")")
        Stop-Tree ([int]$parts[1])
      }
    }
    Remove-Item $PidsFile -Force
    Log "stopped; pids file removed"
  } else {
    Log "no pids file ($PidsFile); nothing to stop"
  }
  exit 0
}

if (-not (Test-Path $DocDir)) { Log "DocDir not found: $DocDir"; exit 1 }
if (-not (Test-Path (Join-Path $DocDir 'package.json'))) { Log "not a pnpm workspace: $DocDir"; exit 1 }

# check required tools
foreach ($tool in @('node', 'pnpm', 'bun')) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    Log "missing tool: $tool. Install with: npm install -g $tool"; exit 1
  }
}

# .env (NEXT_PUBLIC_APP_URL; missing => home page 500)
$envSample = Join-Path $V4Dir '.env.example'
$envFile = Join-Path $V4Dir '.env'
if (-not (Test-Path $envFile)) {
  if (Test-Path $envSample) { Copy-Item $envSample $envFile; Log "created .env from .env.example" }
  else { Log "missing .env.example; create .env with NEXT_PUBLIC_APP_URL=http://localhost:$Port"; exit 1 }
}

# install deps
if (-not (Test-Path (Join-Path $DocDir 'node_modules'))) {
  Log "node_modules missing, running pnpm install (first run ~1min)..."
  Push-Location $DocDir
  pnpm install --no-frozen-lockfile
  Pop-Location
}

# build check: shadcn CLI dist + registry JSON (missing => next ERR_MODULE_NOT_FOUND / stale styles)
$cliDist = Join-Path $DocDir 'packages\shadcn\dist\index.js'
$regJson = Join-Path $V4Dir 'public\r\index.json'
if (-not (Test-Path $cliDist) -or -not (Test-Path $regJson)) {
  Log "packages not built, running registry:build (~2min)..."
  Push-Location $DocDir
  pnpm --filter=v4 registry:build
  Pop-Location
}

# port check
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
  $op = $busy[0].OwningProcess
  Log "port $Port already in use (PID $op). Access it directly, or use -Stop first / pick -Port"
  exit 1
}

$nextBin = Join-Path $V4Dir 'node_modules\next\dist\bin\next'
$tsxCli = Join-Path $DocDir 'node_modules\tsx\dist\cli.mjs'
if (-not (Test-Path $nextBin)) { Log "next bin not found: $nextBin"; exit 1 }
if (-not (Test-Path $tsxCli)) {
  $tsxCli = Join-Path $V4Dir 'node_modules\tsx\dist\cli.mjs'
}

Log "starting icon watcher + next dev (port $Port, host $HostName)..."
$nextLog = Join-Path $DocDir 'next.log'
$nextErr = Join-Path $DocDir 'next.err.log'
$iconsLog = Join-Path $DocDir 'icons.log'
$iconsErr = Join-Path $DocDir 'icons.err.log'

# icon watcher (optional; hot-rebuild icons on source change)
if (Test-Path $tsxCli) {
$icons = Start-Process -FilePath 'node' -ArgumentList @($tsxCli, '--tsconfig', './tsconfig.scripts.json', './scripts/build-icons.ts', '--watch') `
  -WorkingDirectory $V4Dir -WindowStyle Hidden `
  -RedirectStandardOutput $iconsLog -RedirectStandardError $iconsErr -PassThru
  Add-Content $PidsFile ("icons|" + $icons.Id)
  Log ("icon watcher PID " + $icons.Id)
} else {
  Log "tsx not found, skip icon watcher"
}

$next = Start-Process -FilePath 'node' -ArgumentList @($nextBin, 'dev', '--turbopack', "--port $Port", "-H $HostName") `
  -WorkingDirectory $V4Dir -WindowStyle Hidden `
  -RedirectStandardOutput $nextLog -RedirectStandardError $nextErr -PassThru
Add-Content $PidsFile ("next|" + $next.Id)
Log ("next dev PID " + $next.Id)

# wait until ready (first compile 30-90s)
$url = "http://$HostName`:$Port"
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 3
  if (Test-Url $url) { $ready = $true; break }
}

if ($ready) {
  Log "docs site ready: $url"
  Log "stop: powershell -File tools/shadcn-docs.ps1 -Stop"
} else {
  Log "startup timeout, check logs: $nextLog / $nextErr"
  exit 1
}
