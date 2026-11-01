$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset batch is busy; inventory production has not started.'}
    & python (Join-Path $PSScriptRoot 'author_icon.py') *> (Join-Path $PSScriptRoot 'inventory-production.log')
    $taskExit=$LASTEXITCODE
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'inventory-production.log') -Tail 12
    exit $taskExit
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
