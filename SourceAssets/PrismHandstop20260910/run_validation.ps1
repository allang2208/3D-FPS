param([string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'))
$ErrorActionPreference='Stop'
if($RunId -notmatch '^[a-zA-Z0-9_-]{1,24}$'){throw 'Use a unique short run ID.'}
$root='D:/FPS3D/FPSGAME'
$out=Join-Path $PSScriptRoot $RunId
if(Test-Path -LiteralPath $out){throw 'Run output already exists.'}
New-Item -ItemType Directory -Path $out | Out-Null
$log=Join-Path $out 'runtime.log'
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX=1600 -ResY=900 -ForceRes -unattended -nosplash -nosound -PrismHandstopAudit -ColdSteelProfile=PrismHandstopAudit_{1} -abslog="{2}"' -f $root,$RunId,$log
$process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(!$process.WaitForExit(180000)){throw "Owned audit process $($process.Id) timed out: $log"}
$text=[IO.File]::ReadAllText($log)
if($process.ExitCode -ne 0 -or $text -notmatch 'PRISM_AUDIT COMPLETE checks=\d+ failures=0' -or $text -match 'PRISM_AUDIT FAIL'){throw "Prism audit failed: $log"}
foreach($name in @('side','rotated','first-person','all-parts')){Copy-Item -LiteralPath "$root/Saved/PrismHandstopAudit/prism-$name.png" -Destination $out}
Write-Output "PASS prism handstop: $log"
