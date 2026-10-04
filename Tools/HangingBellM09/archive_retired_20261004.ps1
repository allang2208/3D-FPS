param([switch]$Apply)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME')
$sourceRoot=Join-Path $project 'SourceAssets/HangingBellM09Meshy20261003'
$trashRoot=Join-Path $project 'trash/m09-retired-20261004'
$manifest=Join-Path $project 'Docs/Monsters/HangingBellM09Archive20261004.json'
if($Apply -and (Test-Path -LiteralPath $manifest)){throw 'This closeout is already archived; preserve its manifest'}
$choices=@{}
function Add-Retired([string]$Path,[string]$Reason) {
 $absolute=[IO.Path]::GetFullPath($Path)
 if(-not $absolute.StartsWith($project+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Source outside project'}
 if(Test-Path -LiteralPath $absolute -PathType Leaf){$choices[$absolute]=$Reason}
}
foreach($file in Get-ChildItem -LiteralPath $sourceRoot -File -Recurse) {
 $relative=[IO.Path]::GetRelativePath($sourceRoot,$file.FullName).Replace('\','/')
 if($relative -match '(^|/)Before/' -or $file.Extension -eq '.blend1' -or $file.Name -match '-backup-') {
  Add-Retired $file.FullName 'Superseded rollback or automatic backup; recoverable in trash'
 } elseif($relative -match '^(ResonanceV06|ClawBodyDriveV17)/') {
  Add-Retired $file.FullName 'Standalone old production output replaced by V09/V07 or V18; no active author input'
 } elseif($relative -match '^CrownClawV11/(Authoring|Exports)/') {
  Add-Retired $file.FullName 'V11 claw result replaced; donor_motion.json retained as V15 input'
 }
}
foreach($relative in @(
 'Authoring/M09_Separated_Adjusted_v01.blend','Exports/M09_Separated_Adjusted_v01.fbx','Exports/M09_Separated_Adjusted_v01.glb',
 'Records/parts_recipe_v01.json','Records/delivery_v01.json','Records/blender_authoring.log','Records/semantic_build.log','README.txt',
 'MotionV04/Exports/A_M09_Claw.fbx','MotionV04/Exports/A_M09_Death.fbx','MotionV04/Exports/A_M09_Gaze.fbx','MotionV04/Exports/A_M09_Resonance.fbx',
 'ResonanceV07/Authoring/M09_Resonance_V07.blend','ResonanceV07/Exports/A_M09_Resonance_V07.fbx')) {
 Add-Retired (Join-Path $sourceRoot $relative) 'Superseded standalone result; current mixed-version source chain retained'
}
$toolRoot=Join-Path $project 'Tools/HangingBellM09'
foreach($file in Get-ChildItem -LiteralPath $toolRoot -File) {
 if($file.Name -match '(resonance.*v06|ResonanceV06|claw_body_drive.*v17)') {
  Add-Retired $file.FullName 'Retired author/import/build entrypoint superseded by active versions'
 }
}
foreach($name in @('repair_arm_socket_surfaces_v16.py','complete_portal_v04.py','document_spawn_v05.py',
 'finish_grip_contact_v04.py','finish_runtime_v04.py','fix_author_indentation.py','integrate_runtime_v04.py',
 'prepare_room_only_v04.py','refine_attachment_groups_v02.py','relax_spawn_v05.py','repair_build_v04.py',
 'record_delivery_v04.py','integrate_resonance_v07.py','end_play_for_opening_import_v09.py')) {
 Add-Retired (Join-Path $toolRoot $name) 'Failed socket retessellation or completed one-time source/editor migration; current source is authoritative'
}
$entries=@(foreach($path in $choices.Keys | Sort-Object) {
 $source=(Resolve-Path -LiteralPath $path).Path
 $relative=[IO.Path]::GetRelativePath($project,$source).Replace('\','/')
 $destination=[IO.Path]::GetFullPath((Join-Path $trashRoot $relative))
 if(-not $destination.StartsWith($trashRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Destination outside task trash'}
 if(Test-Path -LiteralPath $destination){throw ('Destination already exists: '+$destination)}
 [ordered]@{source=$relative;destination=[IO.Path]::GetRelativePath($project,$destination).Replace('\','/');bytes=(Get-Item -LiteralPath $source).Length;sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower();reason=$choices[$path]}
})
$totalBytes=0L;foreach($entry in $entries){$totalBytes+=$entry.bytes}
if(-not $Apply){[ordered]@{files=$entries.Count;bytes=$totalBytes;entries=$entries}|ConvertTo-Json -Depth 5;exit 0}
# All resolved absolute source/destination paths have been checked above. Use
# native PowerShell file moves end-to-end, with hash confirmation per file.
foreach($entry in $entries) {
 $from=Join-Path $project $entry.source;$to=Join-Path $project $entry.destination
 New-Item -ItemType Directory -Path (Split-Path -Parent $to) -Force | Out-Null
 Move-Item -LiteralPath $from -Destination $to
 if((Get-FileHash -LiteralPath $to -Algorithm SHA256).Hash.ToLower() -ne $entry.sha256){throw ('Archive hash mismatch: '+$entry.source)}
}
[ordered]@{date='2026-10-04';scope='HangingBellM09';files=$entries.Count;bytes=$totalBytes;verified=$true;entries=$entries}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $manifest -Encoding utf8
Write-Output ('M09_ARCHIVED '+$entries.Count+' files')
