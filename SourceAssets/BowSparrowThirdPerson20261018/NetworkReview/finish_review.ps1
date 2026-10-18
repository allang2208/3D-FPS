param([int[]]$IsolatedEditorPids=@())
$ErrorActionPreference='Stop'
$bowTask='D:/FPS3D/FPSGAME/SourceAssets/BowSparrowThirdPerson20261018'
$bowReviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bowReviewHeld=$false
try{
    Write-Output 'Waiting for the shared UE review batch.'
    try{$bowReviewHeld=$bowReviewGate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$bowReviewHeld=$true}
    if(-not $bowReviewHeld){throw 'UE review batch remained busy.'}
    & "$bowTask/build.ps1" -Target Editor -IsolatedEditorPids $IsolatedEditorPids
    if($LASTEXITCODE -ne 0){throw 'Editor build incomplete.'}
    & "$bowTask/run_commandlet.ps1" -Stage save -QueueWaitSeconds 0
    if($LASTEXITCODE -ne 0){throw 'V3 asset save incomplete.'}
    python "$bowTask/publish.py"
    if($LASTEXITCODE -ne 0){throw 'Saved V3 set not ready for publication.'}
    python "$PSScriptRoot/check_authoring.py" *> "$PSScriptRoot/authoring-console.log"
    if($LASTEXITCODE -ne 0){throw 'Authoring or active cook coverage check failed.'}
    & "$PSScriptRoot/run_isolated.ps1"
    if($LASTEXITCODE -ne 0){throw 'Isolated presentation checks failed.'}
    & "$PSScriptRoot/run_wire.ps1" -SkipBuild
    if($LASTEXITCODE -ne 0){throw 'Wire presentation checks failed.'}
    & "$bowTask/build.ps1" -Target Game
    if($LASTEXITCODE -ne 0){throw 'Game build incomplete.'}
    python "$PSScriptRoot/finalize_review.py"
    if($LASTEXITCODE -ne 0){throw 'Review receipt incomplete.'}
    python "$bowTask/finalize_delivery.py"
    if($LASTEXITCODE -ne 0){throw 'Delivery receipt incomplete.'}
}finally{if($bowReviewHeld){$bowReviewGate.ReleaseMutex()};$bowReviewGate.Dispose()}
