$ErrorActionPreference = 'Stop'
$taskAnnounced = $false
while ($true) {
    $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject'
    })
    if ($taskEditors.Count -eq 0) { break }
    if (-not $taskAnnounced) { Write-Output 'Waiting for the existing FPSGAME editor to exit; no editor was closed.'; $taskAnnounced = $true }
    Start-Sleep -Seconds 15
}
& (Join-Path $PSScriptRoot 'run_import.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Pistol firing audio import did not complete.' }
& (Join-Path $PSScriptRoot 'build_editor.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Pistol audio routing build did not complete.' }
Write-Output 'PISTOL_AUDIO_ASSETS_AND_NATIVE_BUILD_SAVED'