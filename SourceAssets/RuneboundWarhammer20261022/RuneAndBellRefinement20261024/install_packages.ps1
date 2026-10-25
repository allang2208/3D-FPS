$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){Write-Output 'Asset batch busy; no files changed';exit 75}
    & 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe' ($taskRoot+'\install_packages.py')
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
