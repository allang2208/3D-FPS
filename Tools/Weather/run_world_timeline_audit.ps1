param([string]$Label='final')
$ErrorActionPreference='Stop'
$weatherRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$weatherExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$weatherLog=Join-Path $weatherRoot "Saved/WeatherWorldAudit20260912/$Label.log"
$weatherArgs="`"$weatherRoot/FPSGAME.uproject`" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX=1280 -ResY=720 -RenderOffscreen -unattended -nosound -nosplash -WeatherWorldAudit -ColdSteelProfile=WeatherWorld_$Label -abslog=`"$weatherLog`""
$weatherProcess=Start-Process -FilePath $weatherExe -ArgumentList $weatherArgs -WindowStyle Hidden -PassThru
Write-Output "Weather/world timeline audit PID=$($weatherProcess.Id) log=$weatherLog"
$weatherProcess.WaitForExit()
Select-String -LiteralPath $weatherLog -Pattern 'WEATHER_WORLD_CLOCK|WEATHER_WORLD_RESULT|WEATHER_WORLD_AUDIT|WEATHER_WORLD_CHECK FAIL'
if(!(Select-String -LiteralPath $weatherLog -SimpleMatch 'WEATHER_WORLD_AUDIT_PASS' -Quiet)){throw "Weather/world audit failed: $weatherLog"}
