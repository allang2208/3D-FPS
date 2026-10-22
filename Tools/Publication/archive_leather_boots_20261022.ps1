param([ValidateSet('archive','restore')][string]$Operation='archive')
$ErrorActionPreference='Stop'
$bootRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bootRecords=Join-Path $bootRoot 'Docs/Publication/LeatherBoots20261022'
$bootTrash=[IO.Path]::GetFullPath((Join-Path $bootRoot 'trash/leather-boots-retired-20261022'))
$bootPlan=Get-Content -LiteralPath (Join-Path $bootRecords 'archive-plan.json') -Raw | ConvertFrom-Json
$bootPending=@()
foreach($row in $bootPlan.files){
    $source=[IO.Path]::GetFullPath((Join-Path $bootRoot $row.source))
    $destination=[IO.Path]::GetFullPath((Join-Path $bootRoot $row.destination))
    if(-not $source.StartsWith($bootRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or -not $destination.StartsWith($bootTrash+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Archive path outside the reviewed project scope.'}
    if($Operation -eq 'restore'){$swap=$source;$source=$destination;$destination=$swap}
    if((Test-Path -LiteralPath $source) -and (Test-Path -LiteralPath $destination)){throw "Both paths exist: $($row.source)"}
    $present=if(Test-Path -LiteralPath $source){$source}else{$destination}
    if(-not (Test-Path -LiteralPath $present -PathType Leaf) -or (Get-FileHash -LiteralPath $present -Algorithm SHA256).Hash -ne $row.sha256){throw "File missing or changed: $present"}
    $bootPending+=@{source=$source;destination=$destination;hash=$row.sha256}
}
foreach($item in $bootPending){
    if(Test-Path -LiteralPath $item.source){
        [void](New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($item.destination)))
        Move-Item -LiteralPath $item.source -Destination $item.destination
    }
    if((Test-Path -LiteralPath $item.source) -or (Get-FileHash -LiteralPath $item.destination -Algorithm SHA256).Hash -ne $item.hash){throw "Move read-back mismatch: $($item.destination)"}
}
$receipt=@{operation=$Operation;files=$bootPending.Count;bytes=($bootPlan.files|Measure-Object -Property bytes -Sum).Sum;all_file_hashes_matched=$true;deleted_files=0;finished_utc=[DateTime]::UtcNow.ToString('o')}
$receipt|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $bootRecords ($Operation+'-receipt.json')) -Encoding utf8
$receipt|ConvertTo-Json -Compress
