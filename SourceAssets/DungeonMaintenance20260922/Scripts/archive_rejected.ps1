param([ValidateSet('sources','mixed_sources','content')][string]$Phase)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath('D:\FPS3D\FPSGAME')
$planPath=Join-Path $projectRoot 'SourceAssets\DungeonMaintenance20260922\Config\retirement.json'
$plan=Get-Content -LiteralPath $planPath -Raw -Encoding UTF8 | ConvertFrom-Json
if($Phase -eq 'content'){
  $installed=Get-Content -LiteralPath (Join-Path $projectRoot 'SourceAssets\DungeonMaintenance20260922\Receipts\install.json') -Raw | ConvertFrom-Json
  if($installed.stage -ne 'map_saved'){throw 'Retire live map references and save before moving content'}
}
$archiveRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot $plan.archive))
if (-not $archiveRoot.StartsWith($projectRoot+'\trash\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Archive root outside project trash'}
New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
$receipt=Join-Path $archiveRoot ('moved-'+$Phase+'.json')
if (Test-Path -LiteralPath $receipt) {throw 'Archive phase already has a receipt; preserve it'}
$records=[Collections.Generic.List[object]]::new()
foreach($entry in $plan.entries | Where-Object phase -EQ $Phase){
  $source=[IO.Path]::GetFullPath($entry.source)
  $expected=[IO.Path]::GetFullPath((Join-Path $projectRoot $entry.relative))
  $destination=[IO.Path]::GetFullPath((Join-Path $archiveRoot $entry.relative))
  if($source -ne $expected -or -not $source.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Source outside exact project scope'}
  if(-not $destination.StartsWith($archiveRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Destination outside trash'}
  if(Test-Path -LiteralPath $destination){throw ('Do not overwrite prior archive '+$destination)}
  $item=Get-Item -LiteralPath $source
  $files=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $source -Recurse -File)}else{@($item)}
  $fileRecords=@(foreach($file in $files){
    $relativeFile=$file.FullName.Substring($projectRoot.Length+1)
    [pscustomobject]@{original=$file.FullName;archived=(Join-Path $archiveRoot $relativeFile);bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash}
  })
  New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
  # Both resolved absolute targets have been bounded above; use one native shell.
  Move-Item -LiteralPath $source -Destination $destination
  $records.Add([pscustomobject]@{original=$source;archived=$destination;files=$fileRecords;reason=$plan.reason})
  $records | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receipt -Encoding UTF8
}
Write-Output ('Archived '+$records.Count+' '+$Phase+' entries to '+$archiveRoot)
