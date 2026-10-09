$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    $taskHeld = $taskGate.WaitOne([TimeSpan]::FromSeconds(60))
    if (-not $taskHeld) { throw 'UE asset window remains busy; no import launched.' }
    $taskExisting = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskRoot/FPSGAME.uproject") })
    foreach ($taskProcess in $taskExisting) {
        Write-Output 'Waiting for the existing background asset process to finish before importing M-05.'
        try { [Diagnostics.Process]::GetProcessById($taskProcess.ProcessId).WaitForExit() } catch [ArgumentException] { }
    }
    $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskRoot/FPSGAME.uproject") })
    if ($taskEditors.Count -gt 0) { throw 'FPSGAME editor has opened; use the live bridge for these assets.' }
    $taskLog = "$taskRoot/SourceAssets/FacelessResearcher20261009/V05/Logs/import-commandlet.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/Tools/FacelessResearcher/import_states_v05.py" -unattended -nosplash -nullrhi -nosound "-abslog=$taskLog" *> "$taskRoot/SourceAssets/FacelessResearcher20261009/V05/Logs/import-stdout.log"
    $taskExit = $LASTEXITCODE
    @{ exit_code=$taskExit; log=$taskLog; runtime_tested=$false; rendered=$false } | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/SourceAssets/FacelessResearcher20261009/V05/import_process.json" -Encoding UTF8
    if ($taskExit -ne 0) { throw "Researcher V05 import exited with code $taskExit; see $taskLog" }
    Write-Output 'Researcher V05 assets saved by background commandlet.'
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
