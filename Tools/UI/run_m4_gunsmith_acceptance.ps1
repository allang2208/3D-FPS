param([int]$Width=1280,[int]$Height=720,[string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'))
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $root 'Saved/M4GunsmithAudit'
New-Item -ItemType Directory -Force $out | Out-Null
foreach($phase in @('write','reload')) {
    $log=Join-Path $out "$RunId-$Width-$phase.log"
    $extra=if($phase -eq 'reload'){' -M4GunsmithLoadAudit'}else{''}
    $args='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -M4GunsmithAudit -ColdSteelProfile=M4GunsmithAudit_{3}_{1} -abslog="{4}"{5}' -f $root,$Width,$Height,$RunId,$log,$extra
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
    if(!$p.WaitForExit(180000)){throw "Audit timed out; inspect owned process $($p.Id): $log"}
    $text=[IO.File]::ReadAllText($log)
    if($p.ExitCode -ne 0 -or $text -notmatch 'M4_GUNSMITH: COMPLETE checks=\d+ failures=0' -or $text -match 'M4_GUNSMITH: FAIL'){throw "Audit failed: $log, exit $($p.ExitCode)"}
    foreach($name in @('m4-gunsmith-panel','m4-holographic-ads','m4-holographic-hip','m4-holographic-fire','m4-holographic-reload','m4-iron-restored')){Copy-Item -LiteralPath (Join-Path $out "$name.png") -Destination (Join-Path $out "$RunId-$Width-$phase-$name.png")}
    Write-Output "PASS $phase $Width x $Height : $log"
}
