param([string]$ProjectRoot='D:/FPS3D/FPSGAME')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\','/')
$taskArchive=[IO.Path]::GetFullPath((Join-Path $taskProject 'trash/azure-dragon-retired-20261005')).TrimEnd('\','/')
$taskRoot=[IO.Path]::GetFullPath((Join-Path $taskProject 'SourceAssets/AzureDragon20261004')).TrimEnd('\','/')
$taskRecords=Join-Path $taskProject 'Docs/Publication/AzureDragon20261005'
$taskPlan=Get-Content -LiteralPath (Join-Path $taskRecords 'archive-plan.json') -Raw | ConvertFrom-Json
$taskMoves=foreach($taskItem in $taskPlan.files | Where-Object {$_.kind -eq 'source'}){
    $taskSource=[IO.Path]::GetFullPath((Join-Path $taskProject $taskItem.source))
    $taskDestination=[IO.Path]::GetFullPath((Join-Path $taskProject $taskItem.destination))
    if(-not $taskSource.StartsWith($taskRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or
       -not $taskDestination.StartsWith($taskArchive+'\',[StringComparison]::OrdinalIgnoreCase)){
        throw "Archive path leaves the authorized Azure source scope: $($taskItem.source)"
    }
    if(Test-Path -LiteralPath $taskDestination){throw "Archive destination already exists: $taskDestination"}
    $taskFile=Get-Item -LiteralPath $taskSource
    $taskHash=(Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash.ToLowerInvariant()
    if($taskFile.Length -ne $taskItem.bytes -or $taskHash -ne $taskItem.sha256){throw "Source changed after planning: $taskSource"}
    [pscustomobject]@{Item=$taskItem;Source=$taskSource;Destination=$taskDestination}
}
$taskResults=[Collections.Generic.List[object]]::new()
foreach($taskMove in $taskMoves){
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($taskMove.Destination)) | Out-Null
    Move-Item -LiteralPath $taskMove.Source -Destination $taskMove.Destination
    $taskReadback=(Get-FileHash -LiteralPath $taskMove.Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    $taskItem=$taskMove.Item
    $taskItem | Add-Member -NotePropertyName readback_sha256 -NotePropertyValue $taskReadback
    $taskResults.Add($taskItem)
    [IO.File]::WriteAllText((Join-Path $taskRecords 'source-archive.json'),(@{complete=$false;files=$taskResults}|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    if($taskReadback -ne $taskItem.sha256){throw "Archive readback mismatch: $($taskMove.Destination)"}
}
[IO.File]::WriteAllText((Join-Path $taskRecords 'source-archive.json'),(@{complete=$true;files=$taskResults}|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Write-Output "AZURE_SOURCE_ARCHIVED files=$($taskResults.Count) readbacks_equal=true"
