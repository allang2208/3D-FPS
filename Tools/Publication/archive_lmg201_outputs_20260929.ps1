$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$recordDir = Join-Path $projectRoot 'Docs/Weapons/lmg201-publication-20260929'
$plan = Get-Content -Raw -LiteralPath (Join-Path $recordDir 'archive-plan.json') | ConvertFrom-Json
$refs = Get-Content -Raw -LiteralPath (Join-Path $recordDir 'archive-references.json') | ConvertFrom-Json
if ($refs.external_referencers.Count -ne 0) { throw 'External package references remain.' }
$archiveRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot $plan.archive_root))
$trashPrefix = [IO.Path]::GetFullPath((Join-Path $projectRoot 'trash')) + [IO.Path]::DirectorySeparatorChar
if (-not $archiveRoot.StartsWith($trashPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escapes project trash.' }
if (Test-Path -LiteralPath $archiveRoot) { throw 'Archive already exists; refusing overwrite.' }
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'UE batch occupied; no files moved.' }
    if (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'") { throw 'UE process running; no packages moved.' }
    $records = [Collections.Generic.List[object]]::new()
    $sources = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($row in $plan.moves) {
        $relative = [string]$row.source
        if (-not ($relative.StartsWith('SourceAssets/LMG20120260927/') -or $relative.StartsWith('Content/Weapons/LMG201/'))) { throw "Out-of-scope source: $relative" }
        if (-not $sources.Add($relative)) { throw "Duplicate source: $relative" }
        $src = (Resolve-Path -LiteralPath (Join-Path $projectRoot $relative)).ProviderPath
        $dst = [IO.Path]::GetFullPath((Join-Path $archiveRoot $relative))
        if (-not $src.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Source escapes project.' }
        if (-not $dst.StartsWith($archiveRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escapes archive.' }
        $item = Get-Item -LiteralPath $src
        if ($item.PSIsContainer) { throw 'Manifest requires exact files.' }
        for ($check = $item; $check -and $check.FullName -ne $projectRoot; $check = Get-Item -LiteralPath (Split-Path -Parent $check.FullName)) {
            if ($check.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point in source path.' }
        }
        $records.Add([pscustomobject]@{source=$relative; destination=($plan.archive_root+'/'+$relative); bytes=$item.Length;
            sha256=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash; reason=$row.reason; replacement=$row.replacement})
    }
    $records | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $recordDir 'archive-manifest.json') -Encoding utf8
    foreach ($row in $records) {
        $dst = Join-Path $projectRoot $row.destination
        New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
        Move-Item -LiteralPath (Join-Path $projectRoot $row.source) -Destination $dst
    }
    foreach ($row in $records) {
        $dst = Join-Path $projectRoot $row.destination
        if ((Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash -ne $row.sha256) { throw "Archive hash mismatch: $dst" }
        if (Test-Path -LiteralPath (Join-Path $projectRoot $row.source)) { throw "Source remained: $($row.source)" }
    }
    $summary = [pscustomobject]@{archive_root=$plan.archive_root; files=$records.Count; bytes=($records | Measure-Object bytes -Sum).Sum;
        packages=$refs.packages.Count; retained_packages=$refs.retained.Count; sha256_readback='matched'; game_tested=$false}
    $summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $recordDir 'archive-summary.json') -Encoding utf8
    $summary | ConvertTo-Json -Compress
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
