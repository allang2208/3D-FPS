$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath('D:\FPS3D\FPSGAME')
$destRoot=[IO.Path]::GetFullPath((Join-Path $root 'trash\HatchetThirdPerson20261106'))
if(-not $destRoot.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Archive escaped workspace.'}
if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved; asset move deferred.'}
$relative=@(
 'Source\FPSGAME\Weapons\Kukri\HatchetHeavyChopRhythm.h',
 'SourceAssets\HatchetDualChopRepair20261106\Arms-moves.json',
 'Content\Weapons\TacticalHatchet20261101\DualChopRepair20261106\Arms\A_HatchetDualCombo3.uasset',
 'SourceAssets\HatchetDualChopRepair20261106\RollbackFirstPerson\Replaced\Weapons\TacticalHatchet20261101\SwiftFalconHeavy\Arms\A_FalconDualCharge.uasset',
 'SourceAssets\HatchetDualChopRepair20261106\RollbackFirstPerson\Replaced\Weapons\TacticalHatchet20261101\SwiftFalconHeavy\Arms\A_FalconDualRelease.uasset'
)
$rows=@()
foreach($rel in $relative){
 $src=[IO.Path]::GetFullPath((Join-Path $root $rel));$dst=[IO.Path]::GetFullPath((Join-Path $destRoot $rel))
 if(-not $src.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or -not $dst.StartsWith($destRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Move escaped declared scope.'}
 if(-not (Test-Path -LiteralPath $src -PathType Leaf)){throw "Missing source: $src"}
 if(Test-Path -LiteralPath $dst){throw "Archive already exists: $dst"}
 $rows+=@{source=$src;destination=$dst;bytes=(Get-Item -LiteralPath $src).Length;sha256=(Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash;reason='First-person candidate withdrawn by user; no active runtime reference';verified=$false}
}
[void](New-Item -ItemType Directory -Force -Path $destRoot)
$manifest=@{scope='Withdrawn first-person hatchet candidates only';rows=$rows;retained=@('Current Jason/Kaitlin third-person animations','Restored original first-person assets and Before backups','Source baselines, active authoring scripts and diagnostic evidence');total_bytes=($rows | Measure-Object bytes -Sum).Sum}
$record=Join-Path $destRoot 'cleanup-manifest.json'
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $record -Encoding utf8
foreach($row in $rows){
 [void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $row.destination))
 Move-Item -LiteralPath $row.source -Destination $row.destination
 if((Get-Item -LiteralPath $row.destination).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $row.destination -Algorithm SHA256).Hash -ne $row.sha256 -or (Test-Path -LiteralPath $row.source)){throw "Archive verification failed: $($row.source)"}
 $row.verified=$true
 $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $record -Encoding utf8
}
$author=Join-Path $root 'SourceAssets\HatchetDualChopRepair20261106\author.py'
$snapshot=Join-Path $destRoot 'author-with-retired-first-person-generator.py'
Copy-Item -LiteralPath $author -Destination $snapshot
Write-Output "ARCHIVED_FILES=$($rows.Count) BYTES=$($manifest.total_bytes) MANIFEST=$record"
