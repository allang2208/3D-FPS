param([switch]$WireOnly)
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'The UE batch gate is still occupied.'}
    & (Join-Path $PSScriptRoot 'build.ps1') *> (Join-Path $PSScriptRoot 'build_console.log')
    if($LASTEXITCODE -ne 0){throw 'Current source build failed; do not execute stale binaries.'}
    if(-not $WireOnly) {
        & (Join-Path $PSScriptRoot 'run_authority.ps1') *> (Join-Path $PSScriptRoot 'authority_console.log')
        if($LASTEXITCODE -ne 0){throw 'M870 authority audit failed; inspect the report before proceeding.'}
    }
    & (Join-Path $PSScriptRoot 'run_wire.ps1') *> (Join-Path $PSScriptRoot 'wire_console.log')
    if($LASTEXITCODE -ne 0){throw 'M870 wire audit failed; inspect both peer logs.'}
    Write-Output 'M870 authority and wire audit completed.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
