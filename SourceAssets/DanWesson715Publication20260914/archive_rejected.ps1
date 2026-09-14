$ErrorActionPreference = 'Stop'
$taskProject = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$taskTrash = [IO.Path]::GetFullPath((Join-Path $taskProject 'trash\dan-wesson715-rejected-models-20260914'))
$taskReferences = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-references.json') -Raw | ConvertFrom-Json
if ($taskReferences.external_referencers.Count -ne 0) { throw 'Resolve external references before archiving.' }
$taskSources = @(
    'SourceAssets/DanWesson715Precision20260914',
    'SourceAssets/DanWesson715Polish20260914',
    'Content/Weapons/DanWesson715/Precision20260914',
    'Content/Weapons/DanWesson715/Polish20260914',
    'Docs/Weapons/dan-wesson715-precision-20260914.md',
    'Docs/Weapons/dan-wesson715-polish-20260914.md'
)
$taskRecords = @()
foreach ($taskRelative in $taskSources) {
    $taskSource = [IO.Path]::GetFullPath((Join-Path $taskProject $taskRelative))
    $taskDestination = [IO.Path]::GetFullPath((Join-Path $taskTrash $taskRelative))
    if (!$taskSource.StartsWith($taskProject + '\', [StringComparison]::OrdinalIgnoreCase) -or
        !$taskDestination.StartsWith($taskTrash + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path escaped task roots.' }
    if (Test-Path -LiteralPath $taskDestination) { throw "Archive already exists: $taskDestination" }
    $taskItem = Get-Item -LiteralPath $taskSource
    $taskFiles = if ($taskItem.PSIsContainer) { @(Get-ChildItem -LiteralPath $taskSource -Recurse -File -Force) } else { @($taskItem) }
    foreach ($taskFile in $taskFiles) {
        $taskOriginal = [IO.Path]::GetRelativePath($taskProject, $taskFile.FullName).Replace('\','/')
        $taskRecords += [pscustomobject]@{
            source = $taskOriginal
            destination = 'trash/dan-wesson715-rejected-models-20260914/' + $taskOriginal
            bytes = $taskFile.Length
            sha256 = (Get-FileHash -LiteralPath $taskFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            reason = 'User rejected the visual result; runtime restored to Chrome.'
            retained = 'Chrome20260914 body; AccessoryPolymer20260914 selected accessories; original author dependency chain.'
        }
    }
}
$taskManifest = Join-Path $PSScriptRoot 'archive-manifest.json'
$taskRecords | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $taskManifest -Encoding utf8NoBOM
foreach ($taskRelative in $taskSources) {
    $taskSource = [IO.Path]::GetFullPath((Join-Path $taskProject $taskRelative))
    $taskDestination = [IO.Path]::GetFullPath((Join-Path $taskTrash $taskRelative))
    # Check every source immediately before the move, including path containment.
    if (!$taskSource.StartsWith($taskProject + '\', [StringComparison]::OrdinalIgnoreCase) -or
        !$taskDestination.StartsWith($taskTrash + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid final archive path.' }
    foreach ($taskRecord in $taskRecords | Where-Object { $_.source -eq $taskRelative -or $_.source.StartsWith($taskRelative + '/') }) {
        if ((Get-FileHash -LiteralPath (Join-Path $taskProject $taskRecord.source) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRecord.sha256) { throw 'Source changed during archive preparation.' }
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $taskDestination) -Force | Out-Null
    Move-Item -LiteralPath $taskSource -Destination $taskDestination
}
foreach ($taskRecord in $taskRecords) {
    $taskArchived = Join-Path $taskProject $taskRecord.destination
    if ((Get-FileHash -LiteralPath $taskArchived -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskRecord.sha256) { throw "Archive hash mismatch: $taskArchived" }
}
$taskSummary = [pscustomobject]@{files=$taskRecords.Count;bytes=($taskRecords|Measure-Object bytes -Sum).Sum;hashes_verified=$true;destination='trash/dan-wesson715-rejected-models-20260914'}
$taskSummary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-summary.json') -Encoding utf8NoBOM
$taskSummary | ConvertTo-Json -Compress
