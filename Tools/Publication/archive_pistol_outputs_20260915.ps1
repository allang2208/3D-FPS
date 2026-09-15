$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$recordDir = Join-Path $projectRoot 'Docs/Weapons/pistol-publication-20260915'
$plan = Get-Content -Raw -LiteralPath (Join-Path $recordDir 'archive-plan.json') | ConvertFrom-Json
$refs = Get-Content -Raw -LiteralPath (Join-Path $recordDir 'archive-references.json') | ConvertFrom-Json
if ($refs.external_referencers.Count -ne 0) { throw 'Archive still has external package referencers.' }
$archiveRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot $plan.archive_root))
$trashPrefix = [IO.Path]::GetFullPath((Join-Path $projectRoot 'trash')) + [IO.Path]::DirectorySeparatorChar
if (-not $archiveRoot.StartsWith($trashPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive escapes project trash.' }
if (Test-Path -LiteralPath $archiveRoot) { throw 'Archive already exists; do not merge or overwrite.' }
$allowedPrefixes = @('SourceAssets/DanWesson715EjectHand20260915','SourceAssets/DanWesson715DonorPress20260915',
    'Content/Weapons/DanWesson715/EjectHand20260915','Content/Weapons/DanWesson715/DonorPress20260915',
    'SourceAssets/PistolDualWield20260914','Content/Weapons/PistolDualWield20260914')
$operations = @()
$records = [Collections.Generic.List[object]]::new()
# Resolve and hash every target before the first move, in one PowerShell shell.
foreach ($row in $plan.moves) {
    $relative = [string]$row.source
    if (-not ($allowedPrefixes | Where-Object { $relative -eq $_ -or $relative.StartsWith($_ + '/') })) { throw "Unapproved archive path: $relative" }
    $src = (Resolve-Path -LiteralPath (Join-Path $projectRoot $relative)).ProviderPath
    $dst = [IO.Path]::GetFullPath((Join-Path $archiveRoot $relative))
    if (-not $src.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Source escapes project.' }
    if (-not $dst.StartsWith($archiveRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escapes archive.' }
    $item = Get-Item -LiteralPath $src
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Archive target is a reparse point.' }
    $children = if ($item.PSIsContainer) { @(Get-ChildItem -LiteralPath $src -Recurse -Force) } else { @($item) }
    if ($children | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) { throw 'Archive contains a reparse point.' }
    foreach ($file in $children | Where-Object { -not $_.PSIsContainer }) {
        $fileRelative = [IO.Path]::GetRelativePath($projectRoot, $file.FullName).Replace('\','/')
        $records.Add([pscustomobject]@{source=$fileRelative; destination=($plan.archive_root+'/'+$fileRelative);
            bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash;
            reason=$row.reason; replacement=$row.replacement})
    }
    $operations += [pscustomobject]@{source=$src; destination=$dst}
}
$records | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $recordDir 'archive-manifest.json') -Encoding utf8
foreach ($operation in $operations) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $operation.destination) -Force | Out-Null
    Move-Item -LiteralPath $operation.source -Destination $operation.destination
}
foreach ($record in $records) {
    $destination = Join-Path $projectRoot $record.destination
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $record.sha256) { throw "Archive hash mismatch: $destination" }
    if (Test-Path -LiteralPath (Join-Path $projectRoot $record.source)) { throw "Source remains after archive: $($record.source)" }
}
$summary = [pscustomobject]@{archive_root=$plan.archive_root; moved_roots=$operations.Count; files=$records.Count;
    bytes=($records | Measure-Object -Property bytes -Sum).Sum; package_count=$refs.packages.Count;
    external_referencers=0; sha256_readback='matched'; testing='Archive integrity only; no game tests'}
$summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $recordDir 'archive-summary.json') -Encoding utf8
$summary | ConvertTo-Json -Compress
