param([string[]]$OnlyModes=@('render','surface','panel'),[string[]]$OnlyMaps=@('L_Normandy_FPS_Test','DayNight_Lighting','L_MilitaryTrench_FPS_Test'))
$ErrorActionPreference='Stop'
$rainRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$rainExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$rainResultPath=Join-Path $rainRoot 'Saved/RainUpgrade/validation-results.json'
$rainResults=if(Test-Path -LiteralPath $rainResultPath){@(Get-Content -LiteralPath $rainResultPath -Raw|ConvertFrom-Json)}else{@()}
$rainJobs=@(
    @('L_Normandy_FPS_Test','render','-RainUpgradeAudit -RainLabel=validated'),
    @('DayNight_Lighting','render','-RainUpgradeAudit -RainLabel=validated'),
    @('L_MilitaryTrench_FPS_Test','render','-RainUpgradeAudit -RainLabel=validated'),
    @('L_Normandy_FPS_Test','surface','-RainSurfaceAudit'),
    @('DayNight_Lighting','panel','-WeatherPanelAudit -WeatherPanelCapture'),
    @('L_MilitaryTrench_FPS_Test','panel','-WeatherPanelAudit -WeatherPanelCapture'),
    @('L_Normandy_FPS_Test','panel','-WeatherPanelAudit')
)
foreach($job in $rainJobs) {
    $map=$job[0];$mode=$job[1];$flags=$job[2]
    if($map -notin $OnlyMaps -or $mode -notin $OnlyModes){continue}
    $log=Join-Path $rainRoot "Saved/RainUpgrade/$map-$mode.log"
    $arguments="`"$rainRoot/FPSGAME.uproject`" /Game/GameMaps/$map -game -windowed -ResX=1280 -ResY=720 -RenderOffscreen -unattended -nosound -nosplash -ColdSteelProfile=RainUpgradeAudit $flags -abslog=`"$log`""
    $process=Start-Process -FilePath $rainExe -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Write-Output "Started $map $mode PID=$($process.Id)"
    if(!$process.WaitForExit(240000)) {throw "Validation process $($process.Id) exceeded four minutes: $map $mode"}
    $marker=switch($mode){render{'RAIN_RENDER_AUDIT_PASS'} surface{'RAIN_SURFACE_AUDIT_PASS'} panel{'WEATHER_PANEL_AUDIT_PASS'}}
    $passed=Select-String -LiteralPath $log -SimpleMatch $marker -Quiet
    $rainResults=@($rainResults|Where-Object {!($_.map -eq $map -and $_.mode -eq $mode)})
    $rainResults += [pscustomobject]@{map=$map;mode=$mode;passed=[bool]$passed;log=$log}
    $rainResults | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $rainRoot 'Saved/RainUpgrade/validation-results.json')
    Write-Output "$map $mode pass=$passed"
}
