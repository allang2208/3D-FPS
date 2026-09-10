param([int]$Width=1920,[int]$Height=1080,[string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'))
$ErrorActionPreference='Stop'
if($RunId -notmatch '^[a-zA-Z0-9_-]{1,30}$'){throw 'RunId must be a short filename-safe identifier.'}
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$outputDirectory=Join-Path $projectRoot 'Saved/WeaponHandlingAudit'
New-Item -ItemType Directory -Force $outputDirectory | Out-Null
$logPath=Join-Path $outputDirectory "$RunId-runtime.log"
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosplash -WeaponHandlingAudit -ColdSteelProfile=WeaponHandlingAudit_{3} -FixedSeed -UseFixedTimeStep -FPS=60 -abslog="{4}"' -f $projectRoot,$Width,$Height,$RunId,$logPath
$process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(!$process.WaitForExit(120000)){throw "Owned test process $($process.Id) timed out. Log: $logPath"}
$content=[IO.File]::ReadAllText($logPath)
if($process.ExitCode -ne 0 -or $content -notmatch 'HANDLING_COMPLETE checks=\d+ failures=0' -or $content -match 'HANDLING: FAIL'){throw "Handling audit failed: $logPath"}
foreach($name in @('assertions.csv','settling.csv','handling-panel.png')){
    Copy-Item -LiteralPath (Join-Path $outputDirectory $name) -Destination (Join-Path $outputDirectory "$RunId-$name")
}
Write-Output "PASS handling: $logPath"
