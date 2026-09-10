param([string]$Editor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
$logPath=Join-Path $projectRoot "Saved/InventoryMigration/gunplay-$runId.log"
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX=1280 -ResY=720 -ForceRes -unattended -nosound -NoSplash -GunplayAudit -GunplayLabel=inventory-{1} -ColdSteelProfile=InventoryGunplay_{1} -abslog="{2}"' -f $projectRoot,$runId,$logPath
$auditProcess=Start-Process -FilePath $Editor -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(!$auditProcess.WaitForExit(180000)){
    $auditProcess.Kill()
    throw "Owned gunplay audit timed out: $logPath"
}
$log=[IO.File]::ReadAllText($logPath)
if($auditProcess.ExitCode -ne 0 -or $log -notmatch 'GUNPLAY_ACCEPTANCE_COMPLETE failures=0' -or $log -match 'GUNPLAY_ASSERT FAIL'){
    throw "Gunplay regression failed: $logPath (exit $($auditProcess.ExitCode))"
}
Write-Output "PASS inventory-backed gunplay: $logPath"
