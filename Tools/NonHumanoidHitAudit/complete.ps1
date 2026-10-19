$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; completion batch not started.'}
    # Nested scripts run on this PowerShell thread; the named mutex is reentrant.
    & "$PSScriptRoot/build_native.ps1" -Targets FPSGAMEEditor,FPSGAME -MaximumWaitSeconds 1200 -MaxParallelActions 6 -UseDefaultLiveCodingSupport
    & "$PSScriptRoot/run.ps1" -Label baseline-full
    & "$PSScriptRoot/repair.ps1" -InputLabel baseline-full -Label repair
    & "$PSScriptRoot/run.ps1" -Label after-repair
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
