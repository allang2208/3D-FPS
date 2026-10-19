param([string]$Attempt='01')
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Catalog publication queue timed out'}
    & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'publish_catalog.py')
    if($LASTEXITCODE -ne 0){throw 'Catalog publication failed'}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
& (Join-Path $PSScriptRoot 'build.ps1') -Attempt $Attempt
