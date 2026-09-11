$ErrorActionPreference='Stop'
$gripCmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$gripProject='D:/FPS3D/FPSGAME/FPSGAME.uproject'
# The runtime audit swaps rifles, so both complete families must exist before either run.
$env:FPS_FRONT_FILTER='m4:vertical,akm:vertical'
& $gripCmd $gripProject -run=pythonscript "-script=$PSScriptRoot/import_assets.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$PSScriptRoot/import-opposed.log" *> "$PSScriptRoot/import-opposed-console.log"
if((Get-Content -LiteralPath "$PSScriptRoot/import-opposed.log" -Raw) -notmatch 'FRONT_IMPORT_PASS 18'){throw 'Opposed import failed'}
Remove-Item Env:FPS_FRONT_FILTER
& $gripCmd $gripProject -run=pythonscript "-script=$PSScriptRoot/verify_assets.py" -unattended -nop4 -nosplash -nullrhi "-abslog=$PSScriptRoot/readback-opposed.log" *> "$PSScriptRoot/readback-opposed-console.log"
if((Get-Content -LiteralPath "$PSScriptRoot/readback-opposed.log" -Raw) -notmatch 'FRONT_READBACK_PASS 18'){throw 'Opposed readback failed'}
foreach($gripWeapon in @('m4','akm')){
    & "$PSScriptRoot/run.ps1" -Weapon $gripWeapon -Grip vertical -Run "opposed-$gripWeapon-vertical"
}
Write-Output 'OPPOSED_RUNTIME_ALL_PASS'
