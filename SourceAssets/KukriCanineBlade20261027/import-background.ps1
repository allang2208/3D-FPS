$ErrorActionPreference='Stop'
$canineProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$canineEditors=@(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($canineProject) })
if ($canineEditors.Count) { throw 'Project editor is running; use its existing authoring bridge.' }
# Engine-supported override for asset authoring; no SDK installation/build needed.
# Scope it to this child process and restore the caller's environment afterwards.
$caninePreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $canineProject -run=pythonscript "-script=$PSScriptRoot\import_canine.py" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-abslog=$PSScriptRoot\import-commandlet-sdk-skip.log" *> (Join-Path $PSScriptRoot 'import-console-sdk-skip.log')
    $canineExit=$LASTEXITCODE
} finally {
    if ($null -eq $caninePreviousSDK) { Remove-Item Env:UE_SKIP_UBT_SDK_SETUP -ErrorAction SilentlyContinue } else { $env:UE_SKIP_UBT_SDK_SETUP=$caninePreviousSDK }
}
exit $canineExit
