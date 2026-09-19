$ErrorActionPreference='Stop'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE '-ModuleWithSuffix=FPSGAME,49151' '-ModuleWithSuffix=AutoFootstep,49151' '-ModuleWithSuffix=AutoFootstepEditor,49151' *> (Join-Path $PSScriptRoot 'build.log')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$runeNativeV11=Join-Path $PSScriptRoot 'NativeBuildSnapshot'
New-Item -ItemType Directory -Path ($runeNativeV11+'\FPSGAME'),($runeNativeV11+'\AutoFootstep') -Force | Out-Null
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME-49151.dll','D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV11+'\FPSGAME')
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstep-49151.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstepEditor-49151.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV11+'\AutoFootstep')
