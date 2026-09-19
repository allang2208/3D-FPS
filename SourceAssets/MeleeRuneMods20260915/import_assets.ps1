$ErrorActionPreference = 'Stop'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/SourceAssets/RuneSword20260913/WeightLeftV5/ImportHost/RuneSwordImport.uproject' -run=pythonscript '-script=D:/FPS3D/FPSGAME/SourceAssets/MeleeRuneMods20260915/import_assets.py' -NullRHI -unattended -nosplash '-abslog=D:/FPS3D/FPSGAME/SourceAssets/MeleeRuneMods20260915/import_assets.log' *> 'D:/FPS3D/FPSGAME/SourceAssets/MeleeRuneMods20260915/import_console.log'
exit $LASTEXITCODE
