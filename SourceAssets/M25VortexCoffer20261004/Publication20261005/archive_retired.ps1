$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME')
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot 'SourceAssets/M25VortexCoffer20261004'))
$trashRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot 'trash/m25-retired-20261005'))
$manifestPath=Join-Path $projectRoot 'Docs/AssetArchives/m25-retired-20261005.json'
if(Test-Path -LiteralPath $manifestPath){throw 'Archive receipt already exists; do not repeat the move.'}
$files=@(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File | Where-Object {
    $_.FullName -match '\\(Before|BeforeIntegration|BackupBeforeOptimization|__pycache__)\\' -or
    $_.Name -in @('trellis_candidate_draft.api.json','pipeline_status.json','M25_three_views_no_lightning.zip')
})
$records=@()
foreach($file in $files) {
    $source=[IO.Path]::GetFullPath($file.FullName)
    $relative=$source.Substring($sourceRoot.Length+1)
    $destination=[IO.Path]::GetFullPath((Join-Path $trashRoot $relative))
    if(-not $source.StartsWith($sourceRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or
       -not $destination.StartsWith($trashRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or
       -not $trashRoot.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Archive path outside task roots.'}
    if(Test-Path -LiteralPath $destination){throw ('Destination exists: '+$destination)}
    $reason='Superseded rollback snapshot; current production source and assets retained.'
    if($file.Name -eq 'trellis_candidate_draft.api.json'){$reason='Unsubmitted TRELLIS draft superseded by the user-provided Meshy model.'}
    if($file.Name -eq 'pipeline_status.json'){$reason='Early rig-only status superseded by actual asset receipts and current README.'}
    if($file.Name -eq 'M25_three_views_no_lightning.zip'){$reason='Old duplicate views-only delivery; individual reference images retained.'}
    if($source -match '\\__pycache__\\'){$reason='Generated Python bytecode; maintained Python source retained.'}
    $records += [ordered]@{source=$source.Substring($projectRoot.Length+1).Replace('\','/');destination=$destination.Substring($projectRoot.Length+1).Replace('\','/');bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();reason=$reason}
}
New-Item -ItemType Directory -Force -Path (Split-Path $manifestPath) | Out-Null
[ordered]@{date='2026-10-05';scope='M25VortexCoffer';stage='planned';files=$records} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
foreach($record in $records) {
    $source=Join-Path $projectRoot $record.source
    $destination=Join-Path $projectRoot $record.destination
    New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    if((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $record.sha256){throw ('Archive hash mismatch: '+$destination)}
}
$total=($records | ForEach-Object { $_['bytes'] } | Measure-Object -Sum).Sum
[ordered]@{date='2026-10-05';scope='M25VortexCoffer';stage='archived_hashes_matched';count=$records.Count;bytes=$total;retained='Inputs, RigV01, current animations, recipe dependency chain, original high mesh, optimized game mesh, Content packages and production receipts';files=$records} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Output ('M25_ARCHIVED files='+$records.Count+' bytes='+$total)
