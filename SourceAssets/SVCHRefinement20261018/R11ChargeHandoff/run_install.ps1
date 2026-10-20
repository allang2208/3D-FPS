$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$active=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'"
if($active){throw 'Preserve existing UE processes; do not start another asset writer.'}
$env:UE_SKIP_UBT_SDK_SETUP='1'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/install_profile.py" -unattended -nosplash -nosound -NullRHI "-abslog=$PSScriptRoot/install-final.log"
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
