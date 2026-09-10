param([string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'),[int]$Fps=60)
$ErrorActionPreference='Stop'
if($RunId -notmatch '^[a-zA-Z0-9_-]{1,30}$'){throw 'Use a unique short run identifier.'}
$projectRoot='D:\FPS3D\FPSGAME'
$logPath=Join-Path $PSScriptRoot "$RunId-runtime.log"
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX=1600 -ResY=900 -ForceRes -unattended -nosplash -MuzzleMigrationAudit -ColdSteelProfile=MuzzleMigrationAudit_{1} -FixedSeed -UseFixedTimeStep -FPS={2} -abslog="{3}"' -f $projectRoot,$RunId,$Fps,$logPath
$process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(!$process.WaitForExit(180000)){throw "Owned audit process $($process.Id) timed out: $logPath"}
$log=[IO.File]::ReadAllText($logPath)
if($process.ExitCode -ne 0 -or $log -notmatch 'MUZZLE_MIGRATION_COMPLETE checks=\d+ failures=0' -or $log -match 'MUZZLE_AUDIT FAIL'){throw "Muzzle migration failed: $logPath"}
$outputDir=Join-Path $PSScriptRoot $RunId
New-Item -ItemType Directory -Force $outputDir|Out-Null
Get-ChildItem -LiteralPath (Join-Path $projectRoot 'Saved/MuzzleMigrationAudit') -File | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $outputDir}
Write-Output "PASS muzzle migration: $logPath"
