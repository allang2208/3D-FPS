param([int]$QueueSeconds=3600)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$chargeOut=$PSScriptRoot
$chargeGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$chargeGateHeld=$false
$chargeDeadline=(Get-Date).AddSeconds($QueueSeconds)
try {
    Write-Output 'Waiting for one shared batch to end related PIE and save the charge animations.'
    while (-not $chargeGateHeld) {
        if ((Get-Date) -gt $chargeDeadline) { throw 'Charge asset batch still occupied; exported assets preserved.' }
        try { $chargeGateHeld=$chargeGate.WaitOne(1000) }
        catch [Threading.AbandonedMutexException] { $chargeGateHeld=$true; throw 'Previous asset batch abandoned; no editor operation sent.' }
    }
    $chargeStopOutput=Join-Path $chargeOut ('end_play_batch-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.txt')
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $chargeOut '..\RampageRecoverV9\end_related_play.py') `
        -QueueWaitSeconds 0 -OutputFile $chargeStopOutput -MaxOutputChars 1200
    if ($LASTEXITCODE -ne 0) { throw 'Related PIE end request failed; editor preserved.' }
    # End-play is deferred until the next editor tick. Keep the asset batch
    # reserved across that tick and the replacement save.
    Start-Sleep -Seconds 3
    $chargeSaveOutput=Join-Path $chargeOut ('install_batch-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.txt')
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $chargeOut 'install_assets.py') `
        -QueueWaitSeconds 0 -OutputFile $chargeSaveOutput -MaxOutputChars 2400
    if ($LASTEXITCODE -ne 0) { throw 'Charge asset replacement did not complete; current editor preserved.' }
    Write-Output 'SLAG_V11_INSTALLED_AND_SAVED_EXISTING_EDITOR'
} finally {
    if ($chargeGateHeld) { $chargeGate.ReleaseMutex() }
    $chargeGate.Dispose()
}
