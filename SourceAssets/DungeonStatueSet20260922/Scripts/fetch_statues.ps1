param(
    [string]$Token = $env:SKETCHFAB_TOKEN,
    [string]$Proxy = 'http://127.0.0.1:7897',
    [string[]]$Keys
)
# Downloads the author's source + glb packages for every statue in Config/statues.json.
# curl ignores the WinINET proxy, so 127.0.0.1:7897 is passed explicitly: measured
# 1.5-10 MB/s through the proxy versus 20-36 KB/s direct on this host.
$ErrorActionPreference = 'Stop'
if (-not $Token) { throw 'Token required: pass -Token or set SKETCHFAB_TOKEN' }
$case = Split-Path -Parent $PSScriptRoot
$cfg = Get-Content (Join-Path $case 'Config\statues.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$auth = @{ Authorization = "Token $Token"; Accept = 'application/json' }
$results = @()

foreach ($s in $cfg.statues) {
    if ($Keys -and ($Keys -notcontains $s.key)) { continue }
    $dir = Join-Path $case ('Download\' + $s.key)
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Write-Output ("=== {0} ({1}, {2})" -f $s.title, $s.license, $s.uid)
    $dl = Invoke-RestMethod -Uri "https://api.sketchfab.com/v3/models/$($s.uid)/download" -Headers $auth -TimeoutSec 60
    foreach ($fmt in @('source', 'glb')) {
        if (-not $dl.$fmt) { Write-Output "  [skip] $fmt not offered"; continue }
        $entry = $dl.$fmt
        $name = [System.IO.Path]::GetFileName(([uri]$entry.url).AbsolutePath)
        $dest = Join-Path $dir ("{0}_{1}" -f $fmt, $name)
        Remove-Item $dest -Force -ErrorAction SilentlyContinue
        & $curl -L --fail --silent --show-error -x $Proxy --retry 5 --retry-delay 2 --retry-all-errors `
            --speed-limit 1000 --speed-time 120 --max-time 3600 -o $dest $entry.url
        if ($LASTEXITCODE -ne 0) { throw "curl failed for $($s.key)/$fmt (exit $LASTEXITCODE)" }
        $len = (Get-Item $dest).Length
        Write-Output ("  [done] {0} {1:N1} MB (expected {2:N1} MB, match={3})" -f $fmt, ($len / 1MB), ($entry.size / 1MB), ($len -eq $entry.size))
        $results += [pscustomobject]@{
            key = $s.key; format = $fmt; file = $dest
            bytes = $len; sha256 = (Get-FileHash $dest -Algorithm SHA256).Hash
        }
    }
}

$results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $case 'Receipts\download.json') -Encoding UTF8
Write-Output '--- receipts ---'
$results | ForEach-Object { "{0,-12} {1,-7} {2,8:N1} MB  {3}" -f $_.key, $_.format, ($_.bytes / 1MB), $_.sha256 }
