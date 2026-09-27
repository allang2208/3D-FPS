# Explicitly retired grass experiments only; no UE invocation or permanent deletion.
$ErrorActionPreference = 'Stop'
$grassRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..')).TrimEnd('\')
$grassTrash = [IO.Path]::GetFullPath((Join-Path $grassRoot 'trash/grass-paused-20260927'))
$grassManifest = Join-Path $grassRoot 'Docs/AssetArchives/grass-paused-20260927.json'
if (Test-Path -LiteralPath $grassTrash) { throw 'Archive already exists; do not replay blindly.' }
$grassSources = @(
    'SourceAssets/GrassDeform20260926/BeforeV10-20260926-195540',
    'SourceAssets/GrassDeform20260926/BeforeV10-20260926-195617',
    'SourceAssets/GrassDeform20260926/BeforeV10-20260926-195857',
    'SourceAssets/GrassDeform20260926/BeforeV10-20260926-200029',
    'SourceAssets/GrassDeform20260927/BeforeV11-20260927-102542',
    'SourceAssets/GrassFootstepRepair20260926/BeforeRepair',
    'Tools/GrassDeform/read_authoring_context.py',
    'Docs/WorldGeneration/grass-manual-wiring-retired-20260927.md'
)
$grassRows = @()
foreach ($relative in $grassSources) {
    $source = (Resolve-Path -LiteralPath (Join-Path $grassRoot $relative)).ProviderPath
    $target = [IO.Path]::GetFullPath((Join-Path $grassTrash $relative))
    if (-not $source.StartsWith($grassRoot + '\', [StringComparison]::OrdinalIgnoreCase) -or
        -not $target.StartsWith($grassTrash + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Archive path escaped its root: $relative"
    }
    $item = Get-Item -LiteralPath $source
    $tree = @($item)
    if ($item.PSIsContainer) { $tree += @(Get-ChildItem -LiteralPath $source -Recurse -Force) }
    if ($tree | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
        throw "Archive refuses reparse points: $relative"
    }
    foreach ($file in $tree | Where-Object { -not $_.PSIsContainer }) {
        $fileRelative = $file.FullName.Substring($grassRoot.Length + 1).Replace('\','/')
        $grassRows += [pscustomobject]@{
            original = $fileRelative
            archived = 'trash/grass-paused-20260927/' + $fileRelative
            bytes = $file.Length
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            reason = if ($relative -like '*BeforeRepair') { 'Superseded heat-template puff or wrong-domain decal backup' }
                     elseif ($relative -like '*Before*') { 'Superseded early grass deformation backup; later rollback sets retained' }
                     elseif ($relative -like '*read_authoring*') { 'One-off editor play-world query; no production callers' }
                     else { 'Retired manual material recipe; contradicts current RGB/time RT and MPC contracts' }
        }
    }
}
$grassRecord = [ordered]@{date='2026-09-27'; status='planned'; scope='Paused grass interaction experiments only'; files=$grassRows}
New-Item -ItemType Directory -Path (Split-Path $grassManifest) -Force | Out-Null
$grassRecord | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $grassManifest -Encoding utf8
foreach ($relative in $grassSources) {
    # Exact absolute paths were resolved and bounded above before any move.
    $source = [IO.Path]::GetFullPath((Join-Path $grassRoot $relative))
    $target = [IO.Path]::GetFullPath((Join-Path $grassTrash $relative))
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $target
}
foreach ($row in $grassRows) {
    $path = Join-Path $grassRoot $row.archived
    if ((Get-Item -LiteralPath $path).Length -ne $row.bytes -or
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) {
        throw "Archive integrity mismatch: $($row.archived)"
    }
}
$grassRecord.status = 'archived-and-hash-verified'
$grassRecord['total_files'] = $grassRows.Count
$grassRecord['total_bytes'] = ($grassRows | Measure-Object bytes -Sum).Sum
$grassRecord | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $grassManifest -Encoding utf8
Write-Output "Archived $($grassRows.Count) files; manifest $grassManifest"
