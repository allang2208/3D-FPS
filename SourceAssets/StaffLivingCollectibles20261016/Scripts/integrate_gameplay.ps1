$ErrorActionPreference='Stop'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset batch busy; integration remains prepared'}
    & python (Join-Path $PSScriptRoot 'integrate_gameplay.py')
    if($LASTEXITCODE -ne 0){throw 'Gameplay data installation did not complete'}
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
