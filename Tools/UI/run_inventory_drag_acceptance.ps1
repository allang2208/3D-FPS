param([int[]]$Widths=@(1280,960,1920),[switch]$Quick)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
New-Item -ItemType Directory -Force -Path "$projectRoot/Saved/InventoryDrag" | Out-Null
foreach($width in $Widths){
    $height=[int]($width*9/16)
    $logPath="$projectRoot/Saved/InventoryDrag/$runId-$width.log"
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -ColdSteelInventoryAudit -ColdSteelDragAudit -ColdSteelProfile=InventoryDragAudit_{3}_{1} -abslog="{4}"' -f $projectRoot,$width,$height,$runId,$logPath
    if($Quick){$arguments+=' -ColdSteelDragAuditQuick'}
    $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit(180000)){$audit.Kill();throw "Owned inventory drag audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    if($audit.ExitCode -ne 0 -or $log -notmatch 'InventoryDrag: COMPLETE checks=\d+ failures=0' -or $log -match 'InventoryDrag: FAIL'){throw "Inventory drag audit failed: $logPath (exit $($audit.ExitCode))"}
    Write-Output "PASS $width x $height : $logPath"
}
