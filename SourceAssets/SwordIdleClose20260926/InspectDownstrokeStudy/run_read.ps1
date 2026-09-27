$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(0) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { Write-Output 'Waiting for the existing asset batch mutex.' }
    while (-not $held) {
        try { $held = $gate.WaitOne(30000) } catch [Threading.AbandonedMutexException] { $held = $true }
    }
    # This script only loads Inspect and writes diagnostic JSON to its own folder.
    # Other commandlets can operate on unrelated assets; no packages are saved here.
    # A live GUI editor is inspected through its existing bridge instead.
    $writers = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
        Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or
            ($_.CommandLine -match 'FPSGAME.uproject' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)') })
    if ($writers.Count) { throw 'An FPSGAME asset writer is active; use the existing MCP batch or wait for it.' }
    # A standalone -game process only reads cooked/editor assets; do not stop it.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/read_installed.py" `
        -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$PSScriptRoot/read_installed.log"
    if ($LASTEXITCODE -ne 0) { throw "Sword idle authoring failed ($LASTEXITCODE); see read_installed.log" }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
