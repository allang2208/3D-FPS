$ErrorActionPreference='Stop'
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE *> (Join-Path $PSScriptRoot 'build_stamina_scope.log')
exit $LASTEXITCODE
