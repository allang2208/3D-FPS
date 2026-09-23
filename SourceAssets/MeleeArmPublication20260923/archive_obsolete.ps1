# Scoped, recoverable retirement. No UE process, active animation or save is touched.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$archiveRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'trash/melee-arm-obsolete-20260923'))
if (-not $archiveRoot.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive outside project.' }
$items = @(
    'Source/FPSGAME/Weapons/RuneSwordArmOpeningCapture.cpp',
    'Tools/Weapons/MeleeArmOpeningReview20260923/capture_editor_sequence.py',
    'Tools/Weapons/MeleeArmOpeningReview20260923/capture_highland_poseable.py',
    'Tools/Weapons/MeleeArmOpeningReview20260923/start_capture_pie.json',
    'SourceAssets/ThrustElbowRepair20260923/end_play_for_save.py',
    'SourceAssets/ThrustElbowRepair20260923/end-play-mcp-01.txt',
    'SourceAssets/ThrustElbowRepair20260923/install-mcp-01.txt'
)
$failedFolders = @('HighlandCameraLagCapture','HighlandCaptureV4','HighlandFinalPoseCapture','HighlandPoseCapture','HighlandVerifiedPoseCapture','UECapture','UECaptureV2','UEPythonCapture','UEPythonCaptureV2','UEPythonCaptureV3')
foreach ($folder in $failedFolders) { $items += 'Saved/MeleeArmOpeningReview20260923/' + $folder }
$reviewRoot = Join-Path $projectRoot 'Saved/MeleeArmOpeningReview20260923'
Get-ChildItem -LiteralPath $reviewRoot -File | Where-Object {
    $_.Name -match '^(capture-|highland-capture-|ue-python-capture|poseable-start-|editor-schema-|start-pie-|toolsets-)'
} | ForEach-Object { $items += 'Saved/MeleeArmOpeningReview20260923/' + $_.Name }
$plan = @(); $manifest = @()
foreach ($relative in $items) {
    $source = [IO.Path]::GetFullPath((Join-Path $projectRoot $relative))
    $target = [IO.Path]::GetFullPath((Join-Path $archiveRoot $relative))
    if (-not $source.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Source outside project.' }
    if (-not $target.StartsWith($archiveRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Target outside task archive.' }
    if (-not (Test-Path -LiteralPath $source)) { throw ('Missing planned source: ' + $relative) }
    if (Test-Path -LiteralPath $target) { throw ('Archive collision: ' + $target) }
    $sourceItem = Get-Item -LiteralPath $source
    $files = if ($sourceItem.PSIsContainer) { @(Get-ChildItem -LiteralPath $source -Recurse -File) } else { @($sourceItem) }
    foreach ($file in $files) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw ('Unexpected linked file: ' + $file.FullName) }
        $original = [IO.Path]::GetRelativePath($projectRoot, $file.FullName).Replace('\','/')
        $manifest += [ordered]@{
            original=$original; archived=('trash/melee-arm-obsolete-20260923/' + $original)
            bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            reason='Retired UE capture attempt or completed one-time editor control; not accepted runtime evidence'
            retained='Saved/MeleeArmOpeningReview20260923/CameraLagGeometry; SourceAssets/ThrustElbowRepair20260923; reusable offline readers/renderers'
        }
    }
    $plan += @{Source=$source;Target=$target}
}
$record = [ordered]@{scope='Melee arm opening / camera ordering / thrust elbow support';files=$manifest}
$publicManifest = Join-Path $projectRoot 'Docs/Weapons/melee-arm-archive-20260923.json'
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $publicManifest -Encoding utf8
foreach ($move in $plan) {
    [IO.Directory]::CreateDirectory((Split-Path -Parent $move.Target)) | Out-Null
    Move-Item -LiteralPath $move.Source -Destination $move.Target
}
foreach ($entry in $manifest) {
    $destination = Join-Path $projectRoot $entry.archived
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw ('Archive hash mismatch: ' + $entry.original) }
    if (Test-Path -LiteralPath (Join-Path $projectRoot $entry.original)) { throw ('Source still exists: ' + $entry.original) }
}
Copy-Item -LiteralPath $publicManifest -Destination (Join-Path $archiveRoot 'archive-manifest.json')
@'
# Retired melee-arm capture attempts

These files are recoverable troubleshooting history, not active authoring sources or accepted runtime screenshots.
See archive-manifest.json for original paths, byte sizes, SHA-256 and retained replacements.
The six V1 motion sources, final two elbow-support assets, their rollback backups and successful offline evidence remain at their original locations.
The temporary RuneSwordAuditCommandlet ArmOpeningCapture hook was removed with its retired implementation.
'@ | Set-Content -LiteralPath (Join-Path $archiveRoot 'README.md') -Encoding utf8
[pscustomobject]@{files=$manifest.Count;bytes=($manifest | ForEach-Object { $_['bytes'] } | Measure-Object -Sum).Sum;archive=$archiveRoot} | ConvertTo-Json
