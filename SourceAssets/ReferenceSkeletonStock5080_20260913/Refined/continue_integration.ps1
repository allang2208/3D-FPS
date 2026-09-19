param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$stockAuthorRoot = $PSScriptRoot
$stockProjectRoot = 'D:/FPS3D/FPSGAME'
& "$stockProjectRoot/Tools/Build/Build-Editor.ps1" -EngineRoot $EngineRoot *> "$stockAuthorRoot/build_editor.log"
if ($LASTEXITCODE -ne 0) { throw 'Project build did not complete. See build_editor.log.' }
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$stockProjectRoot/FPSGAME.uproject" -run=pythonscript "-script=$stockAuthorRoot/import_assets.py" -unattended -nosplash -NullRHI -nosound "-abslog=$stockAuthorRoot/import_assets.log" *> "$stockAuthorRoot/import_console.log"
Write-Output "Import process exit: $LASTEXITCODE. Runtime tests remain manual."
