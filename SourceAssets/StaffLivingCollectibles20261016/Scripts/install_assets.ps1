$ErrorActionPreference='Stop'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset batch busy; new authored assets remain staged'}
    & python (Join-Path $PSScriptRoot 'install_assets.py')
    if($LASTEXITCODE -ne 0){throw 'Asset installation did not complete'}
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
