$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskArchive=[IO.Path]::GetFullPath((Join-Path $taskRoot 'trash/hills-village-lifecycle-20261118'))
$taskPub=Join-Path $taskRoot 'Docs/Publication/HillsVillageLifecycle20261118'
$taskRows=Get-Content -LiteralPath (Join-Path $taskPub 'retired-files.json') -Raw|ConvertFrom-Json
$taskDone=0
foreach($row in $taskRows){
 $src=[IO.Path]::GetFullPath((Join-Path $taskRoot $row.source))
 $dst=[IO.Path]::GetFullPath((Join-Path $taskRoot $row.destination))
 if(-not $src.StartsWith($taskRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
    -not $dst.StartsWith($taskArchive+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){
  throw "Path outside declared archive: $src -> $dst"
 }
 if(Test-Path -LiteralPath $dst){throw "Archive already exists: $dst"}
 $item=Get-Item -LiteralPath $src -Force
 if($row.kind -eq 'junction'){
  if(-not($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Link changed: $src"}
 }elseif($item.Length -ne $row.bytes -or (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256){throw "Source changed: $src"}
 New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($dst))|Out-Null
 # Move the junction itself; never enumerate or move its production target.
 Move-Item -LiteralPath $src -Destination $dst
 if($row.kind -eq 'junction'){
  if(-not((Get-Item -LiteralPath $dst -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "Archived link missing: $dst"}
 }elseif((Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256){throw "Archive hash mismatch: $dst"}
 $taskDone++
}
@{completed=$taskDone;files=@($taskRows|Where-Object kind -eq 'file').Count;junctions=@($taskRows|Where-Object kind -eq 'junction').Count;bytes=($taskRows|Measure-Object bytes -Sum).Sum;sha256_readback=$true;permanent_delete=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskPub 'archive-receipt.json')
Write-Output "Archived and verified $taskDone entries."
