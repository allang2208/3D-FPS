param([switch]$WarehouseOnly)
$ErrorActionPreference='Stop'
if(!$WarehouseOnly){
    & "$PSScriptRoot/run_inventory_drag_acceptance.ps1" -Quick
    & "$PSScriptRoot/run_inventory_acceptance.ps1" -Widths 1280
}
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
New-Item -ItemType Directory -Force -Path "$projectRoot/Saved/WarehouseMigration" | Out-Null
foreach($phase in @('write','reload')){
    $logPath="$projectRoot/Saved/WarehouseMigration/drag-parity-$runId-$phase.log"
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX=1280 -ResY=720 -ForceRes -unattended -nosound -NoSplash -ColdSteelWarehouseAudit -ColdSteelProfile=WarehouseDragAudit_{1} -abslog="{2}"' -f $projectRoot,$runId,$logPath
    if($phase -eq 'reload'){$arguments+=' -WarehouseLoadAudit'}
    $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit(180000)){$audit.Kill();throw "Owned warehouse audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    if($audit.ExitCode -ne 0 -or $log -notmatch 'WarehouseAudit: COMPLETE checks=\d+ failures=0' -or $log -match 'WarehouseAudit: FAIL'){throw "Warehouse regression failed: $logPath"}
    Write-Output "PASS warehouse $phase : $logPath"
}
