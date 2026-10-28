$ErrorActionPreference='Stop'
$runeProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$runeEditors=@(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($runeProject) })
if ($runeEditors.Count) { throw 'Project editor is running; preserve its loaded assets and use the existing authoring bridge.' }
$runePreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $runeProject -run=pythonscript "-script=$PSScriptRoot\import_assets.py" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-abslog=$PSScriptRoot\import-commandlet.log" *> (Join-Path $PSScriptRoot 'import-console.log')
    $runeExit=$LASTEXITCODE
} finally {
    if ($null -eq $runePreviousSDK) { Remove-Item Env:UE_SKIP_UBT_SDK_SETUP -ErrorAction SilentlyContinue } else { $env:UE_SKIP_UBT_SDK_SETUP=$runePreviousSDK }
}
exit $runeExit
