$ErrorActionPreference = 'Stop'
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$cmd = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$proj = 'D:\FPS3D\FPSGAME\FPSGAME.uproject'
$script = 'D:\FPS3D\FPSGAME\Tools\WorldGeneration\VillageStable\PropsR43\apply_and_verify.py'
$log = 'D:\FPS3D\FPSGAME\Saved\Logs\StablePropsR43.log'

& $cmd $proj `
  -run=pythonscript `
  "-script=$script" `
  -unattended -nop4 -nosplash -nullrhi -stdout `
  -Multiprocess `
  -asyncStaticMeshCompilation=0 `
  "-abslog=$log"

if ($LASTEXITCODE -ne 0) {
  throw "StablePropsR43 failed with exit code $LASTEXITCODE (see $log)"
}
Write-Host "STABLE_PROPS_R43_PS1_OK"
