param([int]$Width=1280)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
$outputPath=Join-Path $projectRoot 'Saved/DropHitch'
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$logPath=Join-Path $outputPath "$runId-$Width.log"
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -DropHitchAudit -ColdSteelProfile=DropHitchAudit_{3}_{1} -abslog="{4}"' -f $projectRoot,$Width,([int]($Width*9/16)),$runId,$logPath
$audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(!$audit.WaitForExit(180000)){$audit.Kill();throw "Owned drop hitch audit timed out: $logPath"}
$log=[IO.File]::ReadAllText($logPath)
if($audit.ExitCode -ne 0 -or $log -notmatch 'DropHitchAudit: COMPLETE checks=\d+ failures=0' -or $log -match 'DropHitchAudit: FAIL'){throw "Drop hitch audit failed: $logPath (exit $($audit.ExitCode))"}
Select-String -Path $logPath -Pattern 'DropTiming:|DropHitchAudit: COMPLETE' | ForEach-Object Line
Write-Output "PASS: $logPath"
