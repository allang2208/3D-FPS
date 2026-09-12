param([ValidateSet('DayNight_Lighting','L_Normandy_FPS_Test','L_MilitaryTrench_FPS_Test')][string]$Map='DayNight_Lighting',[string]$Label='visibility-final')
$ErrorActionPreference='Stop'
$rainRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$rainExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$rainLog=Join-Path $rainRoot "Saved/RainVisibility20260912/$Map-$Label.log"
$rainArgs="`"$rainRoot/FPSGAME.uproject`" /Game/GameMaps/$Map -game -windowed -ResX=1280 -ResY=720 -RenderOffscreen -unattended -nosound -nosplash -ColdSteelProfile=Rain_$Label -RainUpgradeAudit -RainVisibilityAudit -RainLabel=$Label -abslog=`"$rainLog`""
$rainProcess=Start-Process -FilePath $rainExe -ArgumentList $rainArgs -WindowStyle Hidden -PassThru
Write-Output "Rain visibility audit $Map PID=$($rainProcess.Id)"
$rainProcess.WaitForExit()
Select-String -LiteralPath $rainLog -Pattern 'RAIN_VISIBLE_GPU|RAIN_VISIBILITY_CHECK|PUDDLE_COVERAGE|RAIN_VISIBILITY_AUDIT'
if(!(Select-String -LiteralPath $rainLog -SimpleMatch 'RAIN_VISIBILITY_AUDIT_PASS' -Quiet)){throw "Rain audit failed: $rainLog"}
