$ErrorActionPreference = 'Stop'
# Guard V24 install: background UnrealEditor-Cmd pythonscript, asset-batch mutex, log to the F: batch directory.
$projectRoot = 'D:/FPS3D/FPSGAME'
$batch = 'F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Install-20261122'
New-Item -ItemType Directory -Force $batch | Out-Null
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(0) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { Write-Output 'Waiting for the existing asset batch mutex.' }
    while (-not $held) {
        try { $held = $gate.WaitOne(30000) } catch [Threading.AbandonedMutexException] { $held = $true }
    }
    # Writers of this project's Content only (separate production hosts use their own .uproject).
    $writers = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" |
        Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or
            ($_.CommandLine -match '(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)') })
    if ($writers.Count) { throw 'An FPSGAME asset writer is active; use the existing MCP batch or wait for it.' }
    # A running UBT link needs UnrealEditor-FPSGAME.dll; do not hold it open during someone else's build.
    $builds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object { $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAME' })
    if ($builds.Count) { throw 'An FPSGAME build is running; install after it finishes.' }
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/import_guard_v24.py" `
        -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$batch/import_guard_v24.log"
    $code = $LASTEXITCODE
    $done = Select-String -Path "$batch/import_guard_v24.log" -Pattern 'GUARD_V24_COMPLETE' -Quiet
    if ($code -ne 0 -and -not $done) { throw "Guard V24 import failed ($code); see $batch/import_guard_v24.log" }
    if ($code -ne 0) { Write-Output "Commandlet exit $code after GUARD_V24_COMPLETE (saves already written)." }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
