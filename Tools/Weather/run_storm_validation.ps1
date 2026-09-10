param([string[]]$Maps=@('DayNight_Lighting','L_MilitaryTrench_FPS_Test','L_Normandy_FPS_Test'))
$ErrorActionPreference='Stop'
$stormRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$results=@()
foreach($map in $Maps){
    $log=Join-Path $stormRoot "Saved/StormClouds/$map.log"
    $arguments="`"$stormRoot/FPSGAME.uproject`" /Game/GameMaps/$map -game -windowed -ResX=1280 -ResY=720 -RenderOffscreen -unattended -nosound -nosplash -StormCloudAudit -ColdSteelProfile=StormCloudAudit -abslog=`"$log`""
    $process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Write-Output "Started $map PID=$($process.Id)"
    if(!$process.WaitForExit(240000)){throw "Audit exceeded four minutes: PID=$($process.Id)"}
    $passed=Select-String -LiteralPath $log -SimpleMatch 'STORM_CLOUD_AUDIT_PASS' -Quiet
    $results+=[pscustomobject]@{map=$map;passed=[bool]$passed;log=$log}
    $results|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $stormRoot 'Saved/StormClouds/results.json')
    Write-Output "$map pass=$passed"
}
