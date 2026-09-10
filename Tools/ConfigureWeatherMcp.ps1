param([string]$EditorCmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
$ErrorActionPreference = 'Stop'
# Replaces the retired blue-card generator. Runs separately from animation editors.
$rainProject = Split-Path -Parent $PSScriptRoot
$rainScript = Join-Path $PSScriptRoot 'Weather/build_rain_assets.py'
$rainLog = Join-Path $rainProject 'Saved/RainUpgrade/reconfigure.log'
& $EditorCmd (Join-Path $rainProject 'FPSGAME.uproject') -run=pythonscript "-script=$rainScript" -unattended -nosplash -nullrhi "-abslog=$rainLog"
if (!(Select-String -LiteralPath $rainLog -SimpleMatch 'RAIN_ASSETS_BUILD_PASS' -Quiet)) {
    throw "Rain asset build did not pass. See $rainLog"
}
