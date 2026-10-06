$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'archive-manifest.json')){throw 'This archive is already recorded. Use the existing manifest; do not overwrite its history.'}
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$archiveRoot=Join-Path $taskRoot 'trash/weapon-accessories-20261006'
$prefix=$taskRoot.TrimEnd('\')+'\'
function ScopedPath([string]$Relative){
 $p=[IO.Path]::GetFullPath((Join-Path $taskRoot $Relative))
 if(!$p.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw "Outside project: $p"}
 return $p
}
# These two old-version inputs still produce the current M16 clamp and mount frames.
$inputs=ScopedPath 'SourceAssets/BlessedLaser20261006/Model/MountRepair/Inputs'
New-Item -ItemType Directory -Path $inputs -Force | Out-Null
foreach($pair in @(
 @('SourceAssets/BlessedLaser20261006/Model/MountRepair/Before/authoring.json','authoring-v1.json'),
 @('SourceAssets/BlessedLaser20261006/Model/MountRepair/Before/Fitted/BlessedLaser_M16.blend','BlessedLaser_M16_mount_source.blend')
)){
 $source=ScopedPath $pair[0];$target=Join-Path $inputs $pair[1]
 if(Test-Path -LiteralPath $source){
  if(Test-Path -LiteralPath $target){throw "Input destination already exists: $target"}
  Copy-Item -LiteralPath $source -Destination $target
  if((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash){throw 'Input copy mismatch'}
 }
}
$retired=@(
 'SourceAssets/G18HolographicTransparency20261005/BeforePackages',
 'SourceAssets/BlessedLaser20261006/Model/MountRepair/Before',
 'SourceAssets/LegendaryStock20261006/RefinementV2',
 'SourceAssets/LegendaryStock20261006/RefinementV3/Before',
 'SourceAssets/LegendaryStock20261006/Integration/Before',
 'SourceAssets/RSH12InventoryIcon20261006/BeforeHorizontal',
 'SourceAssets/RSH12InventoryIcon20261006/prepare_delivery_previous.py',
 'SourceAssets/RSH12InventoryIcon20261006/ue_rsh12_previous.png',
 'SourceAssets/RSH12InventoryIcon20261006/ue_rsh12_previous.uasset',
 'SourceAssets/RSH12InventoryIcon20261006/ue_rsh12_horizontal_v2.png',
 'SourceAssets/RSH12Mechanics20261006/BeforeIcon',
 'Tools/Weapons/BlessedLaser20261006/end_play_for_material_save.py',
 'Tools/Weapons/BlessedLaser20261006/save_all.py'
)
foreach($dir in @('SourceAssets/BlessedLaser20261006','SourceAssets/LegendaryStock20261006','SourceAssets/ThermalScope20261006')){
 Get-ChildItem -LiteralPath (ScopedPath $dir) -Recurse -File -Filter '*.blend1' | ForEach-Object {
  $rel=$_.FullName.Substring($prefix.Length).Replace('\','/')
  if(!($retired | Where-Object {$rel.StartsWith($_+'/')})){$retired+=$rel}
 }
}
$records=@();$moves=@()
foreach($rel in $retired){
 $source=ScopedPath $rel
 if(!(Test-Path -LiteralPath $source)){continue}
 $destination=ScopedPath ('trash/weapon-accessories-20261006/'+$rel)
 if(Test-Path -LiteralPath $destination){throw "Archive destination exists: $destination"}
 $item=Get-Item -LiteralPath $source
 $files=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $source -Recurse -File)}else{@($item)}
 foreach($file in $files){
  $original=$file.FullName.Substring($prefix.Length).Replace('\','/')
  $records+=@{original=$original;archived='trash/weapon-accessories-20261006/'+$original;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLower();reason='superseded model/icon/backup or completed one-off helper';replacement='See Docs/Weapons/weapon-accessories-publication-20261006.md'}
 }
 $moves+=@{source=$source;destination=$destination}
}
$records | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-manifest.json') -Encoding UTF8
foreach($move in $moves){
 New-Item -ItemType Directory -Path (Split-Path -Parent $move.destination) -Force | Out-Null
 Move-Item -LiteralPath $move.source -Destination $move.destination
}
foreach($record in $records){
 if((Get-FileHash -LiteralPath (ScopedPath $record.archived) -Algorithm SHA256).Hash.ToLower() -ne $record.sha256){throw "Archive mismatch: $($record.archived)"}
}
Write-Output ('Archived '+$records.Count+' files, '+[math]::Round(($records|Measure-Object bytes -Sum).Sum/1MB,2)+' MiB. No files deleted.')
