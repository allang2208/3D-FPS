param([string]$PlanPath='D:/FPS3D/FPSGAME/SourceAssets/PitViper2011Publication20261003/archive-plan.json')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME').TrimEnd('\','/')
$taskArchive=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME/trash/pit-viper2011-closeout-20261003').TrimEnd('\','/')
$taskReceipt=Join-Path $taskProject 'SourceAssets/PitViper2011Publication20261003/archive-manifest.json'
$taskSourceRoots=@(Get-ChildItem -LiteralPath (Join-Path $taskProject 'SourceAssets') -Directory -Filter 'PitViper*' | ForEach-Object { $_.FullName })
$taskExternal=[IO.Path]::GetFullPath('C:/Users/allan/.codex/generated_images/01a0fb54-2e91-7602-9a0b-39b3c5c8d00f/exec-2424a719-30b1-4362-b54f-5df8f58971ee.png')
$taskHelper=[IO.Path]::GetFullPath((Join-Path $taskProject 'Tools/Weapons/pit_viper_si_interface.py'))
$taskPlan=Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskUtf8=[Text.UTF8Encoding]::new($false)
$taskEntries=[Collections.Generic.List[object]]::new()
$taskReport=[ordered]@{task='Pit Viper 2011 closeout 20261003';archive_root=$taskArchive;complete=$false;file_count=0;bytes=[long]0;files=$taskEntries}
function Write-TaskReceipt {
    $taskReport.file_count=$taskEntries.Count
    [IO.File]::WriteAllText($taskReceipt,($taskReport | ConvertTo-Json -Depth 8)+"`n",$taskUtf8)
}
if(Test-Path -LiteralPath $taskReceipt){throw 'Preserve existing retirement receipt before another archive run.'}
# Resolve the complete plan before moving any file. No recursive shell move.
$taskMoves=foreach($taskItem in $taskPlan.files){
    $taskSource=[IO.Path]::GetFullPath($(if([IO.Path]::IsPathRooted($taskItem.path)){$taskItem.path}else{Join-Path $taskProject $taskItem.path}))
    $taskRelative=if($taskItem.destination_relative){$taskItem.destination_relative}else{$taskItem.path}
    $taskDestination=[IO.Path]::GetFullPath((Join-Path $taskArchive $taskRelative))
    $taskAllowed=$taskSource -eq $taskExternal -or $taskSource -eq $taskHelper
    foreach($taskRoot in $taskSourceRoots){if($taskSource.StartsWith($taskRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){$taskAllowed=$true}}
    if(-not $taskAllowed -or -not $taskDestination.StartsWith($taskArchive+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw "Archive path leaves task scope: $($taskItem.path)"}
    if(-not(Test-Path -LiteralPath $taskSource -PathType Leaf)){throw "Missing archive source: $taskSource"}
    if(Test-Path -LiteralPath $taskDestination){throw "Archive destination exists: $taskDestination"}
    [pscustomobject]@{Item=$taskItem;Source=$taskSource;Destination=$taskDestination}
}
Write-TaskReceipt
foreach($taskMove in $taskMoves){
    $taskFile=Get-Item -LiteralPath $taskMove.Source
    $taskHash=(Get-FileHash -LiteralPath $taskMove.Source -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($taskMove.Destination)) | Out-Null
    Move-Item -LiteralPath $taskMove.Source -Destination $taskMove.Destination
    $taskSaved=Get-Item -LiteralPath $taskMove.Destination
    $taskReadback=(Get-FileHash -LiteralPath $taskMove.Destination -Algorithm SHA256).Hash.ToLowerInvariant()
    $taskEntries.Add([ordered]@{source=$taskMove.Item.path;destination=$taskMove.Destination;bytes=$taskFile.Length;sha256=$taskHash;reason=$taskMove.Item.reason;retained_replacement=$taskMove.Item.replacement;readback_sha256=$taskReadback;readback_equal=($taskSaved.Length -eq $taskFile.Length -and $taskReadback -eq $taskHash)})
    $taskReport.bytes+=$taskFile.Length;Write-TaskReceipt
    if(-not $taskEntries[$taskEntries.Count-1].readback_equal){throw "Archive readback differs: $($taskMove.Destination)"}
}
$taskReport.complete=$true;Write-TaskReceipt
[IO.File]::WriteAllText((Join-Path $taskArchive 'README.md'),"# Pit Viper 2011 recoverable archive`n`nOriginal paths, hashes, reasons and replacements: SourceAssets/PitViper2011Publication20261003/archive-manifest.json`n`nNo files were deleted. Retired source scripts must not overwrite current saved assets.`n",$taskUtf8)
Write-Output "PIT_VIPER_ARCHIVED $($taskReport.file_count) files ($($taskReport.bytes) bytes); all readbacks equal."
