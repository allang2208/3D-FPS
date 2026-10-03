param([string]$Script = 'import_si_compensator.py')
$ErrorActionPreference = 'Stop'
$taskScript = Join-Path $PSScriptRoot $Script
while ($true) {
    try {
        & 'D:/FPS3D/FPSGAME/SourceAssets/WeaponSurface20260930/run_ue.ps1' -Script $taskScript -GateSeconds 120
        if ($LASTEXITCODE -ne 0) { throw "SI import failed ($LASTEXITCODE)." }
        break
    } catch {
        # Only retry known preflight conditions, before any assets were modified.
        if ($_.Exception.Message -notmatch 'An existing project commandlet is running|UE batch gate occupied') { throw }
        if (-not $taskWaitingReported) { Write-Output 'Existing UE batch retained; SI import waits automatically.'; $taskWaitingReported = $true }
        Start-Sleep -Seconds 15
    }
}
