$ErrorActionPreference='Stop'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE -NoLiveCoding '-ModuleWithSuffix=FPSGAME,49157' '-ModuleWithSuffix=AutoFootstep,49157' '-ModuleWithSuffix=AutoFootstepEditor,49157' *> (Join-Path $PSScriptRoot 'build.log')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$runeNativeV17=Join-Path $PSScriptRoot 'NativeBuildSnapshot'
New-Item -ItemType Directory -Path ($runeNativeV17+'\FPSGAME'),($runeNativeV17+'\AutoFootstep') -Force | Out-Null
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME-49157.dll','D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV17+'\FPSGAME')
Copy-Item -LiteralPath 'D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstep-49157.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor-AutoFootstepEditor-49157.dll','D:\FPS3D\FPSGAME\Plugins\AutoFootstep\Binaries\Win64\UnrealEditor.modules' -Destination ($runeNativeV17+'\AutoFootstep')
