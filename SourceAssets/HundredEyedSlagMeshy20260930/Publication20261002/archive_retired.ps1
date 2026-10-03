param([string]$PlanFile='archive-plan.json')
$ErrorActionPreference='Stop'
$projectRoot=(Resolve-Path -LiteralPath 'D:\FPS3D\FPSGAME').Path
$ownedRoot=(Resolve-Path -LiteralPath (Join-Path $projectRoot 'SourceAssets\HundredEyedSlagMeshy20260930')).Path
$archiveRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot 'trash\hundred-eyed-slag-20261002'))
$plan=Get-Content -LiteralPath (Join-Path $PSScriptRoot $PlanFile) -Raw | ConvertFrom-Json
$records=[Collections.Generic.List[object]]::new()
$manifest=Join-Path $PSScriptRoot 'archive-manifest.json'
if(Test-Path -LiteralPath $manifest) {
    $prior=Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    foreach($record in $prior.files) {$records.Add($record)}
}
foreach($entry in $plan) {
    $source=[IO.Path]::GetFullPath((Join-Path $projectRoot $entry.relative))
    $destination=[IO.Path]::GetFullPath((Join-Path $archiveRoot $entry.relative))
    if(-not $source.StartsWith($ownedRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive source escaped the owned task.' }
    if(-not $destination.StartsWith($archiveRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive destination escaped the task trash folder.' }
    if(-not (Test-Path -LiteralPath $source)) { throw ('Archive source missing: '+$entry.relative) }
    if(Test-Path -LiteralPath $destination) { throw ('Archive destination already exists: '+$destination) }
    $item=Get-Item -LiteralPath $source
    $files=if($item.PSIsContainer) { @(Get-ChildItem -LiteralPath $source -Recurse -File) } else { @($item) }
    $batch=@(foreach($file in $files) {
        $suffix=if($item.PSIsContainer) {$file.FullName.Substring($source.Length).TrimStart('\')} else {''}
        $archivedFile=if($suffix) {Join-Path $destination $suffix} else {$destination}
        [pscustomobject]@{
            original=$file.FullName.Substring($projectRoot.Length+1).Replace('\','/')
            archived=$archivedFile.Substring($projectRoot.Length+1).Replace('\','/')
            bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            reason=$entry.reason; retained_replacement=$entry.replacement; readback_matches=$false
        }
    })
    New-Item -ItemType Directory -Path (Split-Path -Path $destination -Parent) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    foreach($record in $batch) {
        $saved=Join-Path $projectRoot $record.archived
        $record.readback_matches=((Get-Item -LiteralPath $saved).Length -eq $record.bytes -and
            (Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash.ToLowerInvariant() -eq $record.sha256)
        $records.Add($record)
        if(-not $record.readback_matches) { throw ('Archive readback mismatch: '+$record.archived) }
    }
    @{
        task='hundred-eyed-slag-20261002'; archive_root='trash/hundred-eyed-slag-20261002'
        files=$records.ToArray(); file_count=$records.Count; recoverable=$true
    } | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $manifest -Encoding utf8
}
Write-Output ('ARCHIVED_Slag_FILES '+$records.Count)
