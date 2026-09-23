param(
    [string]$Token = $env:SKETCHFAB_TOKEN,
    [string]$Proxy = 'http://127.0.0.1:7897',
    [string]$Uid = '2ac78fb5a0eb40f5a02a5b0a9f566abf'
)
# Downloads the SVD source + glb. Routes measured on this host (2026-09-22):
#   api.sketchfab.com  -> direct (proxy tunnel fails TLS here)
#   *.s3.amazonaws.com -> proxy (direct was 28 KB/s, proxy 1.7 MB/s)
$ErrorActionPreference = 'Stop'
if (-not $Token) { throw 'Token required' }
$case = Split-Path -Parent $PSScriptRoot
$dir = 'D:\FPS3D\_sketchfab_goddess\svd'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $case 'Receipts') | Out-Null
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'

& $curl -s --fail --max-time 60 -H "Authorization: Token $Token" -H 'Accept: application/json' `
    -o (Join-Path $dir 'download.json') "https://api.sketchfab.com/v3/models/$Uid/download"
if ($LASTEXITCODE -ne 0) { throw 'manifest request failed' }
$dl = Get-Content (Join-Path $dir 'download.json') -Raw -Encoding UTF8 | ConvertFrom-Json

$proxyArgs = @()
if ($Proxy) { $proxyArgs = @('-x', $Proxy) }
$results = @()
foreach ($fmt in @('source', 'glb')) {
    if (-not $dl.$fmt) { Write-Output "[skip] $fmt"; continue }
    $entry = $dl.$fmt
    $name = [System.IO.Path]::GetFileName(([uri]$entry.url).AbsolutePath)
    $dest = Join-Path $dir ("{0}_{1}" -f $fmt, $name)
    Remove-Item $dest -Force -ErrorAction SilentlyContinue
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $curl -L --fail --silent --show-error @proxyArgs --retry 4 --retry-delay 2 --retry-all-errors `
        --max-time 1800 -o $dest $entry.url
    if ($LASTEXITCODE -ne 0) { throw "curl failed for $fmt (exit $LASTEXITCODE)" }
    $sw.Stop()
    $len = (Get-Item $dest).Length
    Write-Output ("[done] {0} {1:N1} MB in {2:N1}s match={3}" -f $fmt, ($len / 1MB), $sw.Elapsed.TotalSeconds, ($len -eq $entry.size))
    $results += [pscustomobject]@{ format = $fmt; file = $dest; bytes = $len
                                   sha256 = (Get-FileHash $dest -Algorithm SHA256).Hash }
}
$results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $case 'Receipts\download.json') -Encoding UTF8
$results | ForEach-Object { "{0,-7} {1,8:N1} MB  {2}" -f $_.format, ($_.bytes / 1MB), $_.sha256 }
