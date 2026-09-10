param([int[]]$Widths=@(1280,960,1920),[switch]$CaptureGlints)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
New-Item -ItemType Directory -Force -Path "$projectRoot/Saved/InventoryVisual" | Out-Null
foreach($width in $Widths){
    $height=[int]($width*9/16);$logPath="$projectRoot/Saved/InventoryVisual/$runId-$width.log"
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -ColdSteelInventoryAudit -InventoryVisualAudit -ColdSteelProfile=InventoryVisualAudit_{3}_{1} -abslog="{4}"' -f $projectRoot,$width,$height,$runId,$logPath
    if($CaptureGlints){$arguments+=' -InventoryCornerGlintAudit'}
    $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit(180000)){$audit.Kill();throw "Owned inventory visual audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    if($audit.ExitCode -ne 0 -or $log -notmatch 'InventoryVisualAudit: COMPLETE checks=\d+ failures=0' -or $log -match 'InventoryVisualAudit: FAIL'){throw "Inventory visual audit failed: $logPath (exit $($audit.ExitCode))"}
    Write-Output "PASS $width x $height : $logPath"
}
