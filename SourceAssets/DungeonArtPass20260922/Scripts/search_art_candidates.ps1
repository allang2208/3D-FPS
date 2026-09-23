param(
    [string]$Token = $env:SKETCHFAB_TOKEN,
    [string]$OutDir = 'D:\FPS3D\_sketchfab_goddess\artpass',
    [int]$PerTerm = 24,
    [string]$Proxy = ''   # e.g. http://127.0.0.1:7897 ; empty = direct
)
# Screens licensed candidates for the dungeon art pass: commercial-friendly only
# (CC0 / CC-BY), downloadable, small enough to be set dressing.
$ErrorActionPreference = 'Stop'
if (-not $Token) { throw 'Token required' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$auth = @{ Authorization = "Token $Token"; Accept = 'application/json' }

$terms = @(
    # --- industrial dressing ---
    'rusty oil drum', 'steel barrel', 'jerry can', 'wooden crate old', 'ammo crate',
    'toolbox worn', 'gas cylinder', 'industrial pipe set', 'pressure gauge industrial',
    'valve wheel', 'electrical panel industrial', 'junction box',
    'cable spool', 'industrial chain', 'winch hoist', 'fire extinguisher old',
    'metal bucket', 'pallet wood', 'industrial lamp cage', 'warning sign metal',
    # --- ruin / masonry ---
    'broken column', 'roman column ruin', 'amphora', 'stone urn', 'carved stone fragment',
    'rubble pile stone', 'ancient stone block', 'sarcophagus', 'ruin wall fragment',
    'stone corbel', 'medieval stone arch', 'broken pottery',
    # --- atmosphere detail ---
    'candle holder old', 'oil lantern', 'cobweb', 'animal skull', 'bone pile',
    'rope coil', 'burlap sack', 'old book stack', 'wooden ladder old', 'rusty grate'
)

$rows = @()
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$tmp = Join-Path $env:TEMP 'sf_search_artpass.json'
# Proxy is optional: 2026-09-22 evening the system proxy was switched off and its tunnel
# stopped completing TLS to api.sketchfab.com, while direct API access answers in ~3 s.
$proxyArgs = @()
if ($Proxy) { $proxyArgs = @('-x', $Proxy) }
foreach ($t in $terms) {
    foreach ($lic in @('cc0', 'by')) {
        $url = "https://api.sketchfab.com/v3/models/search?type=models&downloadable=true&q=" +
               [uri]::EscapeDataString($t) + "&count=$PerTerm&license=$lic"
        $url = "https://api.sketchfab.com/v3/search?type=models&downloadable=true&q=" +
               [uri]::EscapeDataString($t) + "&count=$PerTerm&license=$lic"
        & $curl -s --fail --max-time 60 @proxyArgs -H "Authorization: Token $Token" `
            -H 'Accept: application/json' -o $tmp $url 2>$null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $tmp)) {
            Write-Output "FAIL $t/$lic (curl exit $LASTEXITCODE)"
            continue
        }
        $r = Get-Content $tmp -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($m in $r.results) {
            $rows += [pscustomobject]@{
                term = $t; name = $m.name; uid = $m.uid; faces = $m.faceCount
                license = $m.license.label; user = $m.user.displayName
                views = $m.viewCount; likes = $m.likeCount
                textures = $m.textureCount; url = $m.viewerUrl
            }
        }
    }
}
$rows = $rows | Sort-Object uid -Unique
$rows | Export-Csv (Join-Path $OutDir 'candidates.csv') -NoTypeInformation -Encoding UTF8
Write-Output ("candidates: {0}" -f $rows.Count)

Write-Output '--- by license ---'
$rows | Group-Object license | Sort-Object Count -Descending | Select-Object Count, Name | Format-Table -AutoSize | Out-String -Width 90

Write-Output '--- top per term (CC0 first, then CC-BY; <=250k tris) ---'
foreach ($t in $terms) {
    $best = $rows | Where-Object { $_.term -eq $t -and [int]$_.faces -le 250000 } |
        Sort-Object @{e = { if ($_.license -match 'CC0') { 0 } else { 1 } } }, @{e = { -[int]$_.likes } } |
        Select-Object -First 3
    if (-not $best) { Write-Output ("{0,-28} (none)" -f $t); continue }
    Write-Output ("== {0}" -f $t)
    foreach ($b in $best) {
        Write-Output ("   {0,-42} {1,-30} {2,8} tris  {3,5} likes  {4}" -f
            $b.name, $b.license, $b.faces, $b.likes, $b.uid)
    }
}
