$ErrorActionPreference = 'Stop'
$TaskProjectRoot = 'D:\FPS3D\FPSGAME'
$TaskSourceRoot = $PSScriptRoot
$TaskImportPath = Join-Path $TaskSourceRoot 'import_assets.py'
$TaskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$TaskEditor = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
if ($TaskEditor) {
    & (Join-Path $TaskProjectRoot 'Tools\AssetPipeline\mcp_call_codex.ps1') -PythonScript $TaskImportPath -QueueWaitSeconds 300 -OutputFile (Join-Path $TaskSourceRoot "bridge-import-$TaskStamp.json") -MaxOutputChars 2500
    exit $LASTEXITCODE
}
$TaskBusy = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','link.exe')
}
if ($TaskBusy) { $TaskBusy | Select-Object ProcessId,Name,CommandLine | Format-List; exit 23 }
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $TaskProjectRoot 'FPSGAME.uproject') -run=pythonscript "-script=$TaskImportPath" -nullrhi -unattended -nosplash -stdout "-abslog=$TaskSourceRoot\import-engine-$TaskStamp.log" *> "$TaskSourceRoot\import-commandlet-$TaskStamp.log"
exit $LASTEXITCODE
