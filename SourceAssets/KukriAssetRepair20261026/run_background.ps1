param([string]$Script='read_failure.py',[string]$Run='read-failure')
$ErrorActionPreference = 'Stop'
$batchRoot = $PSScriptRoot
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$gateHeld = $false
try {
    $gateHeld = $gate.WaitOne([TimeSpan]::FromSeconds(600))
    if (-not $gateHeld) { throw 'UE import window busy; no commandlet started.' }
    if (Get-Process -Name 'UnrealEditor','UnrealEditor-Cmd' -ErrorAction SilentlyContinue) { throw 'Editor running; use existing locked bridge.' }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript "-script=$batchRoot\$Script" -unattended -nosplash -nop4 -nullrhi "-abslog=$batchRoot\$Run.log" *> "$batchRoot\$Run-console.log"
    $result=$LASTEXITCODE
} finally {
    if ($gateHeld) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
exit $result
