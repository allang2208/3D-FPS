param(
    [string]$Token = $env:SKETCHFAB_TOKEN,
    [string]$OutDir = 'D:\FPS3D\_sketchfab_goddess\artpass\download',
    [string]$Proxy = '',
    [string]$Keys = ''
)
# Downloads source + glb for every entry in Config/props.json.
# The proxy is optional: 2026-09-22 evening the system proxy was switched off and its
# tunnel stopped completing TLS to Sketchfab, while direct access works.
$ErrorActionPreference = 'Stop'
if (-not $Token) { throw 'Token required' }
$case = Split-Path -Parent $PSScriptRoot
$cfg = Get-Content (Join-Path $case 'Config\props.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$proxyArgs = @()
if ($Proxy) { $proxyArgs = @('-x', $Proxy) }
$only = @()
if ($Keys) { $only = $Keys.Split(',') }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $case 'Receipts') | Out-Null

$results = @()
foreach ($p in $cfg.props) {
    if ($only.Count -and ($only -notcontains $p.key)) { continue }
    $dir = Join-Path $OutDir $p.key
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Output ("=== {0} ({1})" -f $p.title, $p.uid)
    $metaFile = Join-Path $dir 'model.json'
    & $curl -s --fail --max-time 60 @proxyArgs -H "Authorization: Token $Token" `
        -H 'Accept: application/json' -o $metaFile "https://api.sketchfab.com/v3/models/$($p.uid)/download" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "download manifest failed for $($p.key)" }
    $dl = Get-Content $metaFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($fmt in @('source', 'glb')) {
        if (-not $dl.$fmt) { Write-Output "  [skip] $fmt not offered"; continue }
        $entry = $dl.$fmt
        $name = [System.IO.Path]::GetFileName(([uri]$entry.url).AbsolutePath)
        $dest = Join-Path $dir ("{0}_{1}" -f $fmt, $name)
        Remove-Item $dest -Force -ErrorAction SilentlyContinue
        $sw = [Diagnostics.Stopwatch]::StartNew()
        & $curl -L --fail --silent --show-error @proxyArgs --retry 5 --retry-delay 2 --retry-all-errors `
            --speed-limit 500 --speed-time 120 --max-time 3600 -o $dest $entry.url
        if ($LASTEXITCODE -ne 0) { throw "curl failed for $($p.key)/$fmt (exit $LASTEXITCODE)" }
        $sw.Stop()
        $len = (Get-Item $dest).Length
        Write-Output ("  [done] {0} {1:N1} MB in {2:N0}s (expected {3:N1} MB, match={4})" -f `
            $fmt, ($len / 1MB), $sw.Elapsed.TotalSeconds, ($entry.size / 1MB), ($len -eq $entry.size))
        $results += [pscustomobject]@{
            key = $p.key; format = $fmt; file = $dest; bytes = $len
            sha256 = (Get-FileHash $dest -Algorithm SHA256).Hash
        }
    }
}
$results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $case 'Receipts\download.json') -Encoding UTF8
Write-Output '--- receipts ---'
$results | ForEach-Object { "{0,-14} {1,-7} {2,8:N1} MB  {3}" -f $_.key, $_.format, ($_.bytes / 1MB), $_.sha256 }
