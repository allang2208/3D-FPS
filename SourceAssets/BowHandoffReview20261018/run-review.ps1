$ErrorActionPreference='Stop'
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$reviewHeld=$false
try{
    Write-Output 'Waiting for the shared UE review batch.'
    try{$reviewHeld=$reviewGate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$reviewHeld=$true}
    if(-not $reviewHeld){throw 'Shared UE batch remained busy.'}
    Write-Output 'BOW_HANDOFF_REVIEW_READY'
    & "$PSScriptRoot/build.ps1" -Target Editor -IsolatedEditorPids @(120864)
    if($LASTEXITCODE -ne 0){throw "Editor build deferred or failed: $LASTEXITCODE"}
    & "$PSScriptRoot/run_isolated.ps1"
    if($LASTEXITCODE -ne 0){throw "Isolated handoff checks failed: $LASTEXITCODE"}
    & "$PSScriptRoot/build.ps1" -Target Game
    if($LASTEXITCODE -ne 0){throw "Game build deferred or failed: $LASTEXITCODE"}
    & "$PSScriptRoot/run_wire.ps1" -SkipBuild
    if($LASTEXITCODE -ne 0){throw "Wire handoff checks failed: $LASTEXITCODE"}
}finally{if($reviewHeld){$reviewGate.ReleaseMutex()};$reviewGate.Dispose()}
