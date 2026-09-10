param([int[]]$Widths=@(1920,1280,960))
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'Saved/TopVitals') | Out-Null
foreach($width in $Widths){
    $height=[int]($width*9/16)
    $logPath=Join-Path $projectRoot "Saved/TopVitals/$runId-$width.log"
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -ColdSteelTopVitalsAudit -ColdSteelProfile=TopVitals_{3}_{1} -abslog="{4}"' -f $projectRoot,$width,$height,$runId,$logPath
    $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit(180000)){$audit.Kill();throw "Owned top vitals audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    if($audit.ExitCode -ne 0 -or $log -notmatch 'TopVitals: COMPLETE checks=\d+ failures=0' -or $log -match 'TopVitals: FAIL'){throw "Top vitals audit failed: $logPath (exit $($audit.ExitCode))"}
    Write-Output "PASS $width x $height : $logPath"
}
