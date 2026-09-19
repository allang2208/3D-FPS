param([string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'),[int]$Width=1600,[int]$Height=900)
$ErrorActionPreference='Stop'
if($RunId -notmatch '^[a-zA-Z0-9_-]{1,32}$'){throw 'Use a unique short run ID.'}
$root='D:/FPS3D/FPSGAME'
$out=Join-Path $PSScriptRoot $RunId
if(Test-Path -LiteralPath $out){throw 'Run output already exists.'}
New-Item -ItemType Directory -Path $out | Out-Null
foreach($phase in @('write','reload')){
    $log=Join-Path $out "$phase.log"
    $extra=if($phase -eq 'reload'){' -M4GunsmithLoadAudit'}else{''}
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosplash -nosound -M4GunsmithAudit -PrismScope2XAudit -ColdSteelProfile=M4GunsmithAudit_Scope2X_{3} -abslog="{4}"{5}' -f $root,$Width,$Height,$RunId,$log,$extra
    $process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$process.WaitForExit(180000)){throw "Owned audit process $($process.Id) timed out: $log"}
    $text=[IO.File]::ReadAllText($log)
    if($process.ExitCode -ne 0 -or $text -notmatch 'M4_GUNSMITH: COMPLETE checks=\d+ failures=0' -or $text -match 'M4_GUNSMITH: FAIL'){throw "Panoramic audit failed: $log"}
    foreach($name in @('m4-gunsmith-panel','m4-holographic-ads','m4-holographic-hip','m4-holographic-fire','m4-holographic-reload','m4-iron-restored','panoramic-side','panoramic-rotated','panoramic-gameplay-ads','panoramic-inventory-icon')){Copy-Item -LiteralPath "$root/Saved/PrismScope2XAudit/$name.png" -Destination (Join-Path $out "$phase-$name.png")}
    Write-Output "PASS scope2x $phase : $log"
}
