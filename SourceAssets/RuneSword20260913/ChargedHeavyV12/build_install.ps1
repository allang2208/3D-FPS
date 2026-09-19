$ErrorActionPreference='Stop'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE -NoLiveCoding '-ModuleWithSuffix=FPSGAME,61433' '-ModuleWithSuffix=AutoFootstep,61433' '-ModuleWithSuffix=AutoFootstepEditor,61433' *> (Join-Path $PSScriptRoot 'build.log')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$runeNativeV12=Join-Path $PSScriptRoot 'NativeBuildSnapshot'
New-Item -ItemType Directory -Path ($runeNativeV12+'\FPSGAME'),($runeNativeV12+'\AutoFootstep') -Force | Out-Null
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME-61433.dll','D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV12+'\FPSGAME')
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstep-61433.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstepEditor-61433.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV12+'\AutoFootstep')


