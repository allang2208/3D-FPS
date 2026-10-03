$ErrorActionPreference = 'Stop'
$ProjectRoot = 'D:\FPS3D\FPSGAME'
$TaskSource = $PSScriptRoot
$TaskImport = Join-Path $TaskSource 'import_assets.py'
$TaskEditor = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
    Where-Object { $_.CommandLine -match 'FPSGAME' }
if ($TaskEditor) {
    & (Join-Path $ProjectRoot 'Tools\AssetPipeline\mcp_call_codex.ps1') -PythonScript $TaskImport -QueueWaitSeconds 300 -OutputFile (Join-Path $TaskSource ('bridge-import-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')) -MaxOutputChars 2000
    exit $LASTEXITCODE
}
$TaskCommandlet = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" |
    Where-Object { $_.CommandLine -match 'FPSGAME' }
if ($TaskCommandlet) {
    throw 'An FPSGAME commandlet is already running; preserve its asset writes and import in a free background window.'
}
$TaskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $ProjectRoot 'FPSGAME.uproject') -run=pythonscript "-script=$TaskImport" -nullrhi -unattended -nosplash -stdout "-abslog=$TaskSource\import-engine-$TaskStamp.log" *> "$TaskSource\import-commandlet-$TaskStamp.log"
exit $LASTEXITCODE
