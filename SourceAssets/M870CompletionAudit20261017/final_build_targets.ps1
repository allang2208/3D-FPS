$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'The shared UE build batch is occupied.'}
    & (Join-Path $PSScriptRoot 'build.ps1') *> (Join-Path $PSScriptRoot 'final_editor_console.log')
    if($LASTEXITCODE -ne 0){throw 'Final Editor build failed.'}
    & (Join-Path $PSScriptRoot 'build_game.ps1') *> (Join-Path $PSScriptRoot 'final_game_console.log')
    if($LASTEXITCODE -ne 0){throw 'Final Game build failed.'}
    Write-Output 'Final M870 Editor and Game targets built.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
