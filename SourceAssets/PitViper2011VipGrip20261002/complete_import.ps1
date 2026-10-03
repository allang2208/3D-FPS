$ErrorActionPreference = 'Stop'
$taskRunner = 'D:/FPS3D/FPSGAME/SourceAssets/WeaponSurface20260930/run_ue.ps1'
$taskScript = Join-Path $PSScriptRoot 'resume_import.py'
$taskAnnounced = $false
while ($true) {
    try {
        & $taskRunner -Script $taskScript -GateSeconds 120
        if ($LASTEXITCODE -ne 0) { throw 'VIP grip import returned a failure.' }
        Write-Output 'VIP_GRIP_IMPORT_AND_SAVE_COMPLETED'
        break
    } catch {
        if ($_.Exception.Message -notmatch 'No remote-execution node|existing project commandlet') { throw }
        if (-not $taskAnnounced) {
            Write-Output 'Waiting for the existing editor bridge or editor exit; no editor is closed or launched.'
            $taskAnnounced = $true
        }
        Start-Sleep -Seconds 20
    }
}
