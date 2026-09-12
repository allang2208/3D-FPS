param([switch]$Apply)
$ErrorActionPreference='Stop'
$gripRoot=(Resolve-Path -LiteralPath 'D:/FPS3D/FPSGAME').Path
$gripTrash=Join-Path $gripRoot 'trash/grasp-workflow-20260912'
$gripReport=Join-Path $gripRoot 'Docs/Weapons/grasp-archive-20260912.json'
$gripSources=@('SourceAssets/MannyGraspDonor20260912','SourceAssets/VREGripExtensions20260912','SourceAssets/VerticalGripFront20260911')
$gripPlan=[ordered]@{}
function Add-GripArchiveFile($File,$Reason,$Replacement){
    $gripFull=[IO.Path]::GetFullPath($File.FullName)
    $gripAllowed=$false
    foreach($gripScope in $gripSources){if($gripFull.StartsWith((Join-Path $gripRoot $gripScope)+'\',[StringComparison]::OrdinalIgnoreCase)){$gripAllowed=$true}}
    if(!$gripAllowed -or $File.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw "Out-of-scope source: $gripFull"}
    $gripRelative=[IO.Path]::GetRelativePath($gripRoot,$gripFull).Replace('\','/')
    $gripDestination=[IO.Path]::GetFullPath((Join-Path $gripTrash $gripRelative))
    if(!$gripDestination.StartsWith($gripTrash+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid archive destination'}
    if(Test-Path -LiteralPath $gripDestination){throw "Archive destination already exists: $gripDestination"}
    $gripPlan[$gripRelative]=[ordered]@{original=$gripRelative;destination=[IO.Path]::GetRelativePath($gripRoot,$gripDestination).Replace('\','/');bytes=$File.Length;sha256=(Get-FileHash -LiteralPath $gripFull -Algorithm SHA256).Hash.ToLowerInvariant();reason=$Reason;replacement=$Replacement}
}
function Add-GripArchiveTree($Relative,$Reason,$Replacement){
    $gripPath=Join-Path $gripRoot $Relative
    if(Test-Path -LiteralPath $gripPath){Get-ChildItem -LiteralPath $gripPath -File -Recurse | ForEach-Object {Add-GripArchiveFile $_ $Reason $Replacement}}
}
$gripDonor='SourceAssets/MannyGraspDonor20260912'
$gripExtensions='SourceAssets/VREGripExtensions20260912'
$gripFront='SourceAssets/VerticalGripFront20260911'
foreach($gripWeapon in @('m4','akm')){Add-GripArchiveTree "$gripDonor/$gripWeapon" 'Superseded full-closure animation family; current generator writes Final' "$gripDonor/Final/$gripWeapon/vertical"}
foreach($gripName in @('asset_validation.json','build.json','import.json','source_validation.json','render_family.py')){
    Add-GripArchiveFile (Get-Item -LiteralPath (Join-Path $gripRoot "$gripDonor/$gripName")) 'Superseded full-closure report or renderer' "$gripDonor/Final"
}
Add-GripArchiveTree "$gripFront/RejectedForwardThumb" 'Forward-thumb pose rejected; two seed configurations retained byte-for-byte in ReferenceWorkflow/opposed_seed' "$gripDonor/Final"
Add-GripArchiveTree "$gripFront/BeforeReleaseFix" 'Backup before release/return corrections; corrected source remains in m4 and akm' "$gripFront/m4; $gripFront/akm"
Get-ChildItem -LiteralPath (Join-Path $gripRoot $gripFront) -File | Where-Object {$_.Name -match '^candidate_[a-f](?:_|\.)' -or $_.Name -in @('candidates.py','candidate_metrics.json','fit_front.py','prepare_build.py','build_all.ps1')} | ForEach-Object {Add-GripArchiveFile $_ 'Rejected procedural thumb search and its entry points' "$gripDonor/retarget_pose.py; $gripDonor/Final"}
Add-GripArchiveFile (Get-Item -LiteralPath (Join-Path $gripRoot "$gripExtensions/strict_axis_trial.json")) 'Strict shaft alignment caused excessive forearm twist' "$gripExtensions/fits.json; $gripExtensions/canted_clock_audit.json"
foreach($gripScope in $gripSources){
    Get-ChildItem -LiteralPath (Join-Path $gripRoot $gripScope) -Filter '*.blend1' -File -Recurse | ForEach-Object {
        $gripRelative=[IO.Path]::GetRelativePath($gripRoot,$_.FullName).Replace('\','/')
        if(!$gripPlan.Contains($gripRelative)){
            $gripPrimary=$_.FullName.Substring(0,$_.FullName.Length-1)
            if(!(Test-Path -LiteralPath $gripPrimary -PathType Leaf)){throw "Missing paired editable source: $gripPrimary"}
            Add-GripArchiveFile $_ 'Automatic Blender backup; paired current editable file retained' ([IO.Path]::GetRelativePath($gripRoot,$gripPrimary).Replace('\','/'))
        }
    }
}
$gripEntries=@($gripPlan.Values)
$gripTotalBytes=0L
foreach($gripEntry in $gripEntries){$gripTotalBytes+=$gripEntry.bytes}
$gripResult=[ordered]@{date='2026-09-12';scope=$gripSources;status='planned';count=$gripEntries.Count;bytes=$gripTotalBytes;files=$gripEntries}
$gripResult | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $gripReport -Encoding utf8
Write-Output "ARCHIVE_PLAN files=$($gripResult.count) bytes=$($gripResult.bytes)"
if(!$Apply){return}
foreach($gripEntry in $gripEntries){
    $gripSource=Join-Path $gripRoot $gripEntry.original
    $gripDestination=Join-Path $gripRoot $gripEntry.destination
    if((Get-FileHash -LiteralPath $gripSource -Algorithm SHA256).Hash.ToLowerInvariant() -ne $gripEntry.sha256){throw "Source changed: $gripSource"}
    New-Item -ItemType Directory -Path (Split-Path -Parent $gripDestination) -Force | Out-Null
    Move-Item -LiteralPath $gripSource -Destination $gripDestination
    if((Get-FileHash -LiteralPath $gripDestination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $gripEntry.sha256){throw "Archive hash mismatch: $gripDestination"}
}
$gripResult.status='moved_and_sha256_verified'
$gripResult | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $gripReport -Encoding utf8
# Remove only empty directories beneath this task's source roots.
foreach($gripScope in $gripSources){
    Get-ChildItem -LiteralPath (Join-Path $gripRoot $gripScope) -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
        if(!@(Get-ChildItem -LiteralPath $_.FullName -Force).Count){Remove-Item -LiteralPath $_.FullName}
    }
}
Write-Output "ARCHIVE_VERIFIED files=$($gripResult.count) bytes=$($gripResult.bytes)"
