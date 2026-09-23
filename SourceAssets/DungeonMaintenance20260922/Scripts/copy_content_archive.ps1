$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath('D:\FPS3D\FPSGAME')
$plan=Get-Content -LiteralPath (Join-Path $projectRoot 'SourceAssets\DungeonMaintenance20260922\Config\retirement.json') -Raw | ConvertFrom-Json
$archiveRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot $plan.archive))
if(-not $archiveRoot.StartsWith($projectRoot+'\trash\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid trash scope'}
$records=[Collections.Generic.List[object]]::new()
foreach($entry in $plan.entries | Where-Object phase -EQ 'content'){
 $source=[IO.Path]::GetFullPath($entry.source)
 if(-not $source.StartsWith($projectRoot+'\Content\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid content scope'}
 $item=Get-Item -LiteralPath $source
 $files=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $source -File -Recurse)}else{@($item)}
 foreach($file in $files){
  $relative=$file.FullName.Substring($projectRoot.Length+1);$target=[IO.Path]::GetFullPath((Join-Path $archiveRoot $relative))
  if(-not $target.StartsWith($archiveRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid archive target'}
  $sha=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
  New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
  if(Test-Path -LiteralPath $target){if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $sha){throw 'Preserve different archived file'}}
  else{Copy-Item -LiteralPath $file.FullName -Destination $target}
  if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $sha){throw 'Archive copy incomplete'}
  $records.Add([pscustomobject]@{original=$file.FullName;archived=$target;bytes=$file.Length;sha256=$sha})
 }
}
$records | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $archiveRoot 'content-archive.json') -Encoding UTF8
Write-Output ('Content archive saved before editor removal: '+$records.Count+' files')
