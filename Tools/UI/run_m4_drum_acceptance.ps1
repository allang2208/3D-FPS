param([int]$Width=1280,[int]$Height=720,[string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'),[string]$Map='DayNight_Lighting')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $root 'Saved/M4DrumAudit'
New-Item -ItemType Directory -Force $out | Out-Null
foreach($phase in @('write','reload')) {
 $log=Join-Path $out "$RunId-$Width-$phase.log"
 $extra=if($phase -eq 'reload'){' -M4DrumLoadAudit'}else{''}
 $args='"{0}/FPSGAME.uproject" /Game/GameMaps/{6} -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -M4DrumAudit -ColdSteelProfile=M4DrumAudit_{3}_{1} -abslog="{4}"{5}' -f $root,$Width,$Height,$RunId,$log,$extra,$Map
 $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
 if(!$p.WaitForExit(180000)){throw "Audit timed out: owned process $($p.Id), $log"}
 $text=[IO.File]::ReadAllText($log)
 if($p.ExitCode -ne 0 -or $text -notmatch 'M4_DRUM: COMPLETE checks=\d+ failures=0' -or $text -match 'M4_DRUM: FAIL'){throw "Audit failed: $log, exit $($p.ExitCode)"}
 if($text -match 'M4Drum[^\r\n]*Failed to compile Material' -or $text -match 'Failed to find object[^\r\n]*M4Drum'){throw "Drum asset failed to load or compile: $log"}
 foreach($name in @('panel','ads','hip','withdraw','insert','empty-insert','bolt-release','removed')) {
  Copy-Item -LiteralPath (Join-Path $out "drum-$name.png") -Destination (Join-Path $out "$RunId-$Width-$phase-drum-$name.png")
 }
 Write-Output "PASS $phase $Width x $Height : $log"
}
