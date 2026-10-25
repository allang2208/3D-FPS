$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch remains occupied; no check process started.'}
    Write-Output 'HAMMER_CHECK_BATCH_ACQUIRED'
    & (Join-Path $PSScriptRoot 'run_authority.ps1')
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
    & (Join-Path $PSScriptRoot 'run_wire.ps1')
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
    & (Join-Path $PSScriptRoot '../ThirdPersonReview/run_commandlet.ps1') -Stage capture
    exit $LASTEXITCODE
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()
}
