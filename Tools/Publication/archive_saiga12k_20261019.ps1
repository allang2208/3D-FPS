param([ValidateSet('archive','restore')][string]$Operation='archive')
$ErrorActionPreference='Stop'
$s12Root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..')).TrimEnd('\')
$s12Trash=[IO.Path]::GetFullPath((Join-Path $s12Root 'trash/saiga12k-retired-20261019')).TrimEnd('\')
$s12Plan=Get-Content -LiteralPath (Join-Path $s12Root 'SourceAssets/Saiga12KPublication20261019/retired-files.json') -Raw | ConvertFrom-Json
$s12Summary=Get-Content -LiteralPath (Join-Path $s12Root 'Docs/Publication/Saiga12K20261019/archive-plan.json') -Raw | ConvertFrom-Json
if((Get-FileHash -LiteralPath (Join-Path $s12Root $s12Summary.local_manifest) -Algorithm SHA256).Hash -ne $s12Summary.manifest_sha256){throw 'Manifest changed'}
function Get-S12Path([string]$Relative,[string]$Within){
    $absolute=[IO.Path]::GetFullPath((Join-Path $s12Root $Relative))
    if(-not $absolute.StartsWith($Within+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Path outside reviewed root'}
    return $absolute
}
# No active process may be using either retired host; the main editor is retained.
$s12Busy=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'Saiga12K(?:Closure|BodyHands)20261018[\\/]IsolatedHost' }
if($s12Busy){throw 'A reviewed host is still running; preserve it.'}
foreach($group in $s12Plan.groups){
    $source=Get-S12Path $group.source $s12Root;$dest=Get-S12Path $group.destination $s12Trash
    if($Operation -eq 'restore'){$s12Swap=$source;$source=$dest;$dest=$s12Swap}
    if(-not (Test-Path -LiteralPath $source) -or (Test-Path -LiteralPath $dest)){throw 'Missing source or existing destination; preserve both.'}
}
foreach($row in $s12Plan.files){
    $p=Get-S12Path $(if($Operation -eq 'archive'){$row.source}else{$row.destination}) $s12Root
    if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ne $row.sha256){throw ('Changed source: '+$row.source)}
}
foreach($group in $s12Plan.groups){
    $source=Get-S12Path $group.source $s12Root;$dest=Get-S12Path $group.destination $s12Trash
    if($Operation -eq 'restore'){$s12Swap=$source;$source=$dest;$dest=$s12Swap}
    New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $dest
}
foreach($row in $s12Plan.files){
    $p=Get-S12Path $(if($Operation -eq 'archive'){$row.destination}else{$row.source}) $s12Root
    if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -ne $row.sha256){throw ('Move readback mismatch: '+$row.source)}
}
foreach($row in $s12Plan.links){
    $p=Get-S12Path $(if($Operation -eq 'archive'){$row.destination}else{$row.source}) $s12Root
    $item=Get-Item -LiteralPath $p -Force
    if(-not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Missing archived junction'}
}
$s12Receipt=@{operation=$Operation;files=$s12Plan.files.Count;bytes=$s12Summary.bytes;junctions_not_traversed=$s12Plan.links.Count;all_file_hashes_matched=$true;completed=(Get-Date).ToString('o');engine_started=$false;gameplay_tests_run=$false}
$s12Receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $s12Root "Docs/Publication/Saiga12K20261019/$Operation-receipt.json") -Encoding utf8
$s12Receipt | ConvertTo-Json -Compress
