param([int[]]$Widths=@(1920,1280,960),[switch]$CoreOnly,[switch]$GlassOnly)
$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$outputDir=Join-Path $projectRoot 'Saved/WarehouseColdGlass20260912'
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$runId=Get-Date -Format 'yyyyMMddHHmmss'
function Invoke-WarehouseAudit([int]$width,[string]$mode,[string]$profile){
    $height=[int]($width*9/16)
    $logPath=Join-Path $outputDir "$runId-$mode-$width.log"
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -RenderOffscreen -ColdSteelWarehouseAudit -ColdSteelProfile={3} -abslog="{4}"' -f $projectRoot,$width,$height,$profile,$logPath
    if($mode -eq 'glass'){$arguments+=' -WarehouseColdGlassAudit'}
    if($mode -eq 'reload'){$arguments+=' -WarehouseLoadAudit'}
    $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit(240000)){$audit.Kill();throw "Owned warehouse audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    $tag=if($mode -eq 'glass'){'WarehouseGlass'}else{'WarehouseAudit'}
    if($audit.ExitCode -ne 0 -or $log -notmatch "$tag`: COMPLETE checks=\d+ failures=0" -or $log -match "$tag`: FAIL"){throw "Warehouse $mode failed: $logPath (exit $($audit.ExitCode))"}
    Write-Output "PASS $mode $width x $height : $logPath"
}
if(!$GlassOnly){
    $profile="WarehouseSpatialAudit_$runId"
    Invoke-WarehouseAudit 1280 'core' $profile
    Invoke-WarehouseAudit 1280 'reload' $profile
}
if(!$CoreOnly){foreach($width in $Widths){Invoke-WarehouseAudit $width 'glass' "WarehouseGlassAudit_${runId}_$width"}}
