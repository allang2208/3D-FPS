$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Material publication queue timed out.'}
    & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'publish_staged.py')
    if($LASTEXITCODE -ne 0){throw 'Material publication failed; retained staged packages.'}
    @{exit_code=0;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'publication_receipt.json') -Encoding utf8
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()
}
