$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath('D:\FPS3D\FPSGAME')
$plan=Get-Content -LiteralPath (Join-Path $projectRoot 'SourceAssets\DungeonMaintenance20260922\Config\retirement.json') -Raw | ConvertFrom-Json
$archiveRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot $plan.archive))
$state=Get-Content -LiteralPath (Join-Path $projectRoot 'SourceAssets\DungeonMaintenance20260922\Receipts\content-retirement.json') -Raw | ConvertFrom-Json
if($state.stage -ne 'content_archived_and_retired'){throw 'Editor retirement must finish before removing orphaned archive-map packages'}
$removed=[Collections.Generic.List[string]]::new()
foreach($entry in $plan.entries | Where-Object phase -EQ 'content'){
 $source=[IO.Path]::GetFullPath($entry.source)
 if(-not $source.StartsWith($projectRoot+'\Content\',[StringComparison]::OrdinalIgnoreCase)){throw 'Content path outside scope'}
 if(-not (Test-Path -LiteralPath $source)){continue}
 $item=Get-Item -LiteralPath $source
 $files=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $source -Recurse -File)}else{@($item)}
 foreach($file in $files){
  $target=[IO.Path]::GetFullPath((Join-Path $archiveRoot $file.FullName.Substring($projectRoot.Length+1)))
  if(-not $target.StartsWith($archiveRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Archive path outside scope'}
  if(-not (Test-Path -LiteralPath $target)){throw 'Unarchived remaining file; preserve it'}
  if((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $target).Hash){throw 'Changed remaining file; preserve it'}
 }
 # Any residual packages belong to the exact retired roots and have recoverable copies.
 Remove-Item -LiteralPath $source -Recurse -Force
 $removed.Add($source)
}
[pscustomobject]@{stage='complete';residual_paths_removed=$removed;archive=$archiveRoot} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $archiveRoot 'completion.json') -Encoding UTF8
Write-Output 'Recoverable content move completed'
