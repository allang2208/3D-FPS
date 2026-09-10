param([int[]]$Widths=@(1280,960,1920))
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
foreach($width in $Widths){
    $height=[int]($width*9/16)
    $logPath=Join-Path $projectRoot "Saved/ItemTooltip/$runId-$width.log"
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -ColdSteelItemTooltipAudit -ColdSteelProfile=Tooltip_{3}_{1} -abslog="{4}"' -f $projectRoot,$width,$height,$runId,$logPath
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$p.WaitForExit(180000)){$p.Kill();throw "Owned tooltip audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    if($p.ExitCode -ne 0 -or $log -notmatch 'ItemTooltip: COMPLETE checks=\d+ failures=0' -or $log -match 'ItemTooltip: FAIL'){throw "Tooltip audit failed: $logPath (exit $($p.ExitCode))"}
    Write-Output "PASS $width x $height : $logPath"
}
