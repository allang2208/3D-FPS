param([switch]$Resume)
$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$sourceRoot=[IO.Path]::GetFullPath("$project/SourceAssets/M249Orpind20261107")
$archiveRoot=[IO.Path]::GetFullPath("$project/trash/M24920261109")
$plan=Get-Content -Raw -LiteralPath "$project/Docs/Publication/M24920261109/archive-plan.json" | ConvertFrom-Json
New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
$manifest=Join-Path $archiveRoot 'manifest.jsonl'
if((Test-Path -LiteralPath $manifest) -and !$Resume){throw 'Archive manifest already exists; use explicit resume'}
$completed=@();$total=0L
if($Resume){$previous=Get-Content -Raw -LiteralPath (Join-Path $archiveRoot 'receipt.json') | ConvertFrom-Json;$completed=@($previous.completed);$total=[long]$previous.bytes}
$writer=[IO.StreamWriter]::new($manifest,[bool]$Resume,[Text.UTF8Encoding]::new($false))
try {
 foreach($entry in $plan){
  if(@($completed | Where-Object {$_.source -eq $entry.source -and $_.verified}).Count){continue}
  $src=[IO.Path]::GetFullPath($entry.source);$dst=[IO.Path]::GetFullPath($entry.destination)
  if(!$src.StartsWith($sourceRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or !$dst.StartsWith($archiveRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Archive path outside owned boundary'}
  $item=Get-Item -LiteralPath $src
  if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point retained'}
  if(Test-Path -LiteralPath $dst){throw "Destination already exists: $dst"}
  $files=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $src -Recurse -File)}else{@($item)}
  $records=@(foreach($f in $files){
   if($f.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Linked input retained'}
   $target=if($item.PSIsContainer){$dst+$f.FullName.Substring($src.Length)}else{$dst}
   [pscustomobject]@{source=$f.FullName;destination=$target;bytes=$f.Length;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $f.FullName).Hash.ToLowerInvariant();reason=$entry.reason}
  })
  if([long](($records | Measure-Object bytes -Sum).Sum) -ne [long]$entry.bytes){throw "Source changed since planning: $src"}
  New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($dst)) -Force | Out-Null
  foreach($rec in $records){$writer.WriteLine(($rec | ConvertTo-Json -Compress));$writer.Flush()}
  Move-Item -LiteralPath $src -Destination $dst
  foreach($rec in $records){if((Get-Item -LiteralPath $rec.destination).Length -ne $rec.bytes -or (Get-FileHash -Algorithm SHA256 -LiteralPath $rec.destination).Hash.ToLowerInvariant() -ne $rec.sha256){throw "Archive readback mismatch: $($rec.destination)"}}
  $total+=$entry.bytes;$completed+=[pscustomobject]@{source=$src;destination=$dst;files=$records.Count;bytes=$entry.bytes;verified=$true}
  [pscustomobject]@{complete=$false;completed=$completed;bytes=$total} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 -LiteralPath (Join-Path $archiveRoot 'receipt.json')
  Write-Output "Archived and verified: $($src.Substring($sourceRoot.Length+1))"
 }
}finally{$writer.Dispose()}
[pscustomobject]@{complete=$true;completed=$completed;bytes=$total;manifest_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $manifest).Hash.ToLowerInvariant()} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 -LiteralPath (Join-Path $archiveRoot 'receipt.json')
