param([int]$Width=1440,[int]$Height=900,[string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'),[string]$Map='DayNight_Lighting',[switch]$LayoutStress)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $root 'Saved/GunsmithWorkbenchAudit'
New-Item -ItemType Directory -Force $out|Out-Null
$log=Join-Path $out "$RunId-$Width.log"
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/{5} -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -GunsmithWorkbenchAudit -ColdSteelProfile=WorkbenchAudit_{3}_{1} -abslog="{4}"' -f $root,$Width,$Height,$RunId,$log,$Map
if($LayoutStress){$arguments+=' -GunsmithLayoutStress'}
$process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(!$process.WaitForExit(180000)){throw "Workbench audit timeout: owned process $($process.Id), $log"}
$content=[IO.File]::ReadAllText($log)
if($process.ExitCode -ne 0 -or $content -notmatch 'WORKBENCH: COMPLETE checks=\d+ failures=0' -or $content -match 'WORKBENCH: FAIL|GunsmithWorkbench[^\r\n]*Failed to compile Material'){throw "Workbench audit failed: $log"}
foreach($name in @('draft','factory','ads','unequipped','rotated')){Copy-Item -LiteralPath (Join-Path $out "workbench-$name.png") -Destination (Join-Path $out "$RunId-$Width-$name.png")}
if($LayoutStress){Copy-Item -LiteralPath (Join-Path $out 'workbench-scroll.png') -Destination (Join-Path $out "$RunId-$Width-scroll.png")}
Write-Output "PASS $Width x $Height : $log"
