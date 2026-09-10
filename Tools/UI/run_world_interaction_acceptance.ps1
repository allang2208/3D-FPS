param([int]$Width=1280)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
$outputPath=Join-Path $projectRoot 'Saved/WorldInteraction'
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
foreach($phase in @('write','restore')) {
    $logPath=Join-Path $outputPath "$runId-$phase.log"
    $restoreSwitch=if($phase -eq 'restore'){' -WorldInteractionRestoreAudit'}else{''}
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -WorldInteractionAudit -ColdSteelProfile=WorldInteractionAudit_{3} -abslog="{4}"{5}' -f $projectRoot,$Width,([int]($Width*9/16)),$runId,$logPath,$restoreSwitch
    $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit(180000)){$audit.Kill();throw "Owned world interaction audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    if($audit.ExitCode -ne 0 -or $log -notmatch 'WorldInteractionAudit: COMPLETE checks=\d+ failures=0' -or $log -match 'WorldInteractionAudit: FAIL'){throw "World interaction audit failed: $logPath (exit $($audit.ExitCode))"}
    if($phase -eq 'restore' -and $log -notmatch 'PASS fresh process BeginPlay restores saved M4 and AKM models'){throw "Missing fresh process restore proof: $logPath"}
    Write-Output "PASS $phase : $logPath"
}
