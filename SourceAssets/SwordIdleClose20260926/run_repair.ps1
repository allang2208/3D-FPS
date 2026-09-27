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
    $writers = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" |
        Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or
            ($_.CommandLine -match 'FPSGAME.uproject' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)') })
    if ($writers.Count) { throw 'An FPSGAME asset writer is active; use the existing MCP batch or wait for it.' }
    # A standalone -game process only reads cooked/editor assets; do not stop it.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/repair_source_frame_counts.py" `
        -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$PSScriptRoot/repair_source_frame_counts.log"
    if ($LASTEXITCODE -ne 0) { throw "Sword idle authoring failed ($LASTEXITCODE); see repair_source_frame_counts.log" }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
