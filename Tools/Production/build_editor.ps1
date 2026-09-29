$ErrorActionPreference = 'Stop'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development -project='D:\FPS3D\FPSGAME\FPSGAME.uproject' -WaitMutex
Write-Output ('BUILD_EXIT=' + $LASTEXITCODE)
