$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME')
$archive=[IO.Path]::GetFullPath((Join-Path $project 'trash/mantis-m27-retired-20261007'))
$public=Join-Path $project 'Docs/Publication/MantisM27_20261007'
$manifest=Join-Path $public 'archive-manifest.json'
if(Test-Path -LiteralPath $manifest){throw 'Archive manifest already exists; preserve the completed/partial archive and review it before resuming.'}
if(!$archive.StartsWith($project+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Archive escapes project'}
$revisions=@('ClawV7','ClawV12','ClawV13','PounceV9','PounceV10')
$tools=@('author_claw_v7.py','author_claw_v12.py','author_claw_v13.py',
 'import_claw_v7.py','import_claw_v12.py','import_claw_v13.py','finish_claw_v12.ps1','finish_claw_v13.ps1',
 'diagnose_claw_continuity_v12.py','inspect_claw_v12.py','read_ai_v7.py','read_ai_v12.py',
 'read_claw_pose_v7.py','read_scythe_geometry_v13.py','save_combat_v7.py',
 'author_pounce_v9.py','author_pounce_v10.py','import_pounce_v9.py','import_pounce_v10.py',
 'read_pounce_v9_source.py','restore_pounce_v6.py','end_pie_for_binding_v2.py')
$docs=@('MantisM27CombatV7.md','MantisM27ClawV12.md','MantisM27ClawV13.md','MantisM27PounceV9.md','MantisM27PounceV10.md')
$refs=Get-Content -LiteralPath (Join-Path $project 'Saved/MantisM27Publication20261007/asset-references.json') -Raw | ConvertFrom-Json
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$locked=$false
try {
 try{$locked=$gate.WaitOne(600000)}catch [Threading.AbandonedMutexException]{$locked=$true}
 if(!$locked){throw 'UE batch is occupied'}
 if(@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count){throw 'Preserve running UE and retry after it exits'}
 $files=[Collections.Generic.List[object]]::new()
 foreach($rev in $revisions){Get-ChildItem -LiteralPath (Join-Path $project "SourceAssets/MantisM27/$rev") -File -Recurse | ForEach-Object {$files.Add($_)}}
 foreach($name in $tools){$files.Add((Get-Item -LiteralPath (Join-Path $project "Tools/MantisM27/$name")))}
 foreach($name in $docs){$files.Add((Get-Item -LiteralPath (Join-Path $project "Docs/Monsters/$name")))}
 Get-ChildItem -LiteralPath (Join-Path $project 'SourceAssets/MantisM27') -File -Recurse |
  Where-Object {$_.Name -like '*.blend1' -or $_.Name -like '*-backup-*' -or $_.Extension -eq '.pid'} |
  ForEach-Object {$files.Add($_)}
 $cache=Join-Path $project 'Tools/MantisM27/__pycache__'
 if(Test-Path -LiteralPath $cache){Get-ChildItem -LiteralPath $cache -File -Recurse | ForEach-Object {$files.Add($_)}}
 foreach($package in $refs.movable_packages){
  if($package -notmatch '^/Game/Monsters/MantisM27/(ClawV7|ClawV12|ClawV13|PounceV9|PounceV10)/'){throw "Unexpected package: $package"}
  $stem=Join-Path $project ('Content/'+$package.Substring(6))
  foreach($ext in @('.uasset','.uexp','.ubulk')){$path=$stem+$ext;if(Test-Path -LiteralPath $path){$files.Add((Get-Item -LiteralPath $path))}}
 }
 $records=[Collections.Generic.List[object]]::new()
 New-Item -ItemType Directory -Path $public,$archive -Force | Out-Null
 foreach($file in ($files | Sort-Object FullName -Unique)){
  $source=[IO.Path]::GetFullPath($file.FullName)
  if(!$source.StartsWith($project+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw "Source escapes project: $source"}
  $relative=[IO.Path]::GetRelativePath($project,$source)
  $target=[IO.Path]::GetFullPath((Join-Path $archive $relative))
  if(!$target.StartsWith($archive+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw "Target escapes archive: $target"}
  if(Test-Path -LiteralPath $target){throw "Do not overwrite archive: $target"}
  $hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
  $record=[ordered]@{source=$relative.Replace('\','/');destination=([IO.Path]::GetRelativePath($project,$target)).Replace('\','/');bytes=$file.Length;sha256=$hash;reason='Retired M27 candidate, replaced authoring tool, or regenerable previous-save/build residue';retained_replacement='ClawV14 recovery / ClawV16 current; PounceV11 from PounceV6; current source and build receipts';moved=$false}
  $records.Add($record)
  @{task='MantisM27';complete=$false;retained_packages=$refs.retained_packages;files=@($records.ToArray())} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifest -Encoding utf8
  New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target)) -Force | Out-Null
  Move-Item -LiteralPath $source -Destination $target
  if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $hash){throw "Archive hash mismatch: $relative"}
  $record.moved=$true
 }
 $result=@{task='MantisM27';complete=$true;retained_packages=$refs.retained_packages;files=@($records.ToArray())}
 $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifest -Encoding utf8
 Copy-Item -LiteralPath $manifest -Destination (Join-Path $archive 'archive-manifest.json')
 Write-Output ("M27 archive saved: {0} files, {1} bytes" -f $records.Count,(($records|ForEach-Object {[long]$_.bytes}|Measure-Object -Sum).Sum))
}finally{if($locked){$gate.ReleaseMutex()};$gate.Dispose()}
