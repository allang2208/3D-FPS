$ErrorActionPreference='Stop'
$bleedProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$bleedEditors=@(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($bleedProject) })
if ($bleedEditors.Count) { throw 'Project editor is running; use its existing authoring bridge.' }
$bleedPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $bleedProject -run=pythonscript "-script=$PSScriptRoot\author_materials.py" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-abslog=$PSScriptRoot\import-commandlet.log" *> (Join-Path $PSScriptRoot 'import-console.log')
    $bleedExit=$LASTEXITCODE
} finally {
    if ($null -eq $bleedPreviousSDK) { Remove-Item Env:UE_SKIP_UBT_SDK_SETUP -ErrorAction SilentlyContinue } else { $env:UE_SKIP_UBT_SDK_SETUP=$bleedPreviousSDK }
}
exit $bleedExit
