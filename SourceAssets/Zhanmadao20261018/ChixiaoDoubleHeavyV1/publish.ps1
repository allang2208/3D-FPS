$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Publication queue timed out'}
 & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'publish.py')
 if($LASTEXITCODE -ne 0){throw 'Publication failed'}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}