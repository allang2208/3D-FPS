$ErrorActionPreference='Stop'
$gripCmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$gripProject='D:/FPS3D/FPSGAME/FPSGAME.uproject'
$env:FPS_FRONT_FILTER='akm:vertical,akm:prism'
& $gripCmd $gripProject -run=pythonscript "-script=$PSScriptRoot/import_assets.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$PSScriptRoot/import-transition.log" *> "$PSScriptRoot/import-transition-console.log"
if((Get-Content -LiteralPath "$PSScriptRoot/import-transition.log" -Raw) -notmatch 'FRONT_IMPORT_PASS 18'){throw 'Transition import failed'}
Remove-Item Env:FPS_FRONT_FILTER
& $gripCmd $gripProject -run=pythonscript "-script=$PSScriptRoot/verify_assets.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$PSScriptRoot/readback.log" *> "$PSScriptRoot/readback-console.log"
if((Get-Content -LiteralPath "$PSScriptRoot/readback.log" -Raw) -notmatch 'FRONT_READBACK_PASS 36'){throw 'Readback failed'}
foreach($gripVariant in @('vertical','prism')){
    & "$PSScriptRoot/run.ps1" -Weapon akm -Grip $gripVariant -Run "front-akm-$gripVariant-final"
}
Write-Output 'FRONT_TRANSITION_RUNTIME_PASS'
