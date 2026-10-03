$ErrorActionPreference = 'Stop'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
$taskAnnounced = $false
try {
    while ($true) {
        while (-not $taskHeld) {
            try { $taskHeld = $taskGate.WaitOne(15000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
        }
        $taskCommandlets = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject'
        })
        if ($taskCommandlets.Count -eq 0) { break }
        if (-not $taskAnnounced) { Write-Output 'Existing FPSGAME commandlet retained; production import waits.'; $taskAnnounced = $true }
        $taskGate.ReleaseMutex(); $taskHeld = $false
        Start-Sleep -Seconds 15
    }
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
& 'D:/FPS3D/FPSGAME/SourceAssets/WeaponSurface20260930/run_ue.ps1' -Script (Join-Path $PSScriptRoot 'import_assets.py') -GateSeconds 120
if ($LASTEXITCODE -ne 0) { throw 'Common attachment import did not complete.' }
