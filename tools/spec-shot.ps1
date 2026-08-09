# 设计规范页截图编排：起本地服务 -> 无头 Edge --screenshot 截图 -> 清理
$ErrorActionPreference = 'Stop'
$work = Split-Path -Parent $PSScriptRoot
$shotDir = Join-Path $work 'assets\ui\moodboard'
$specW = if ($env:SPEC_W) { $env:SPEC_W } else { '1280' }
$specH = if ($env:SPEC_H) { $env:SPEC_H } else { '1280' }
$outName = if ($env:SPEC_OUT) { $env:SPEC_OUT } else { 'moodboard_final.png' }
$outPng = Join-Path $shotDir $outName
$logOut = Join-Path $env:TEMP 'spec-shot-http.out.log'
$logErr = Join-Path $env:TEMP 'spec-shot-http.err.log'

$http = Start-Process -FilePath 'python' -ArgumentList @('-m', 'http.server', '8899', '--directory', $shotDir) -WorkingDirectory $work -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru
$up = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 500
  if (Get-NetTCPConnection -LocalPort 8899 -State Listen -ErrorAction SilentlyContinue) { $up = $true; break }
}
if (-not $up) { Get-Content $logErr -Tail 10 -ErrorAction SilentlyContinue; exit 1 }

$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$ud = Join-Path $env:TEMP ('edge-cdp-spec-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $ud | Out-Null
if (Test-Path -LiteralPath $outPng) { Move-Item -LiteralPath $outPng -Destination (Join-Path $env:TEMP 'spec-shot-prev.png') -Force }
$ed = Start-Process -FilePath $edge -ArgumentList @('--headless=new', "--user-data-dir=$ud", '--no-first-run', '--disable-gpu', '--hide-scrollbars', "--window-size=$specW,$specH", "--screenshot=$outPng", "http://localhost:8899/spec.html?w=$specW&h=$specH") -WindowStyle Hidden -PassThru
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
  Start-Sleep -Milliseconds 500
  if (Test-Path -LiteralPath $outPng) { $ok = $true; break }
}
Write-Output "png_written=$ok"
$code = if ($ok) { 0 } else { 1 }

$httpConn = Get-NetTCPConnection -LocalPort 8899 -State Listen -ErrorAction SilentlyContinue
if ($httpConn) { Stop-Process -Id $httpConn.OwningProcess -Force -ErrorAction SilentlyContinue }
Stop-Process -Id $ed.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $http.Id -Force -ErrorAction SilentlyContinue
exit $code
