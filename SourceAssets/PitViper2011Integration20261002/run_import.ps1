$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    while ($true) {
        while (-not $taskHeld) {
            try { $taskHeld = $taskGate.WaitOne(15000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
        }
        $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject'
        })
        if ($taskEditors | Where-Object { $_.Name -eq 'UnrealEditor.exe' }) { throw 'An FPSGAME editor is open; use its existing bridge. No editor was stopped.' }
        $taskCompilers = @(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {
            $_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'
        })
        if ($taskEditors.Count -eq 0 -and $taskCompilers.Count -eq 0) { break }
        $taskGate.ReleaseMutex(); $taskHeld = $false
        Start-Sleep -Seconds 15
    }
    # The project launcher reacquires this named mutex on the same PowerShell
    # thread. Its process guard remains authoritative; no editor is opened.
    & (Join-Path $taskProjectRoot 'Tools/ModularOutfit/Run-Authoring.ps1') -Script 'SourceAssets/PitViper2011Integration20261002/import_assets.py' -Log 'SourceAssets/PitViper2011Integration20261002/import_assets.log'
    if ($LASTEXITCODE -ne 0) { throw 'Pit Viper animation import did not complete.' }
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
# Reimporting either authoring family also refreshes the runtime pose deltas.
& (Join-Path $taskProjectRoot 'SourceAssets/WeaponAnimationSharing20261002/run_install.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Pit Viper animation delta production did not complete.' }
