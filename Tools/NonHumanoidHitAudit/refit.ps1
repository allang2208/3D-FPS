$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; refit batch not started.'}
    & "$PSScriptRoot/build_native.ps1" -Targets FPSGAMEEditor,FPSGAME -MaximumWaitSeconds 1200 -MaxParallelActions 6 -UseDefaultLiveCodingSupport
    & "$PSScriptRoot/repair.ps1" -InputLabel baseline-full -Label repair -Refit
    & "$PSScriptRoot/run.ps1" -Label after-repair
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
