$ErrorActionPreference='Stop'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE -NoLiveCoding '-ModuleWithSuffix=FPSGAME,49158' '-ModuleWithSuffix=AutoFootstep,49158' '-ModuleWithSuffix=AutoFootstepEditor,49158' *> (Join-Path $PSScriptRoot 'build.log')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$runeNativeV18=Join-Path $PSScriptRoot 'NativeBuildSnapshot'
New-Item -ItemType Directory -Path ($runeNativeV18+'\FPSGAME'),($runeNativeV18+'\AutoFootstep') -Force | Out-Null
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME-49158.dll','D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV18+'\FPSGAME')
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstep-49158.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstepEditor-49158.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV18+'\AutoFootstep')
