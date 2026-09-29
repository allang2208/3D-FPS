param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$projectRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot '../../..'))
$buildState = Get-Content -LiteralPath (Join-Path $taskRoot 'build-result.json') -Raw | ConvertFrom-Json
if ($buildState.exit_code -ne 0) { throw 'Native build has not completed. Assets have not been imported.' }
$openEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
    [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
})
if ($openEditors.Count -gt 0) { throw 'FPSGAME is open. Use the existing project MCP bridge for this import.' }
$importGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
$oldHeadless = $env:SPITTER_HEADLESS
try {
    try { $held = $importGate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] {
        $held = $true
        throw 'Previous UE asset batch ended unexpectedly. No import was sent.'
    }
    if (-not $held) { throw 'The UE asset batch is busy. No import request was sent.' }
    $env:SPITTER_HEADLESS = '1'
    $exe = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $project = Join-Path $projectRoot 'FPSGAME.uproject'
    $script = Join-Path $taskRoot 'install_locomotion.py'
    $engineLog = Join-Path $taskRoot 'import-headless.log'
    & $exe $project '-run=pythonscript' "-script=$script" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' "-abslog=$engineLog" *> (Join-Path $taskRoot 'import-console.log')
    if ($LASTEXITCODE -ne 0) { throw "Animation import commandlet exited with $LASTEXITCODE. See $engineLog" }
    Write-Output 'Spitter locomotion import commandlet completed. See installation.json for saved assets.'
} finally {
    $env:SPITTER_HEADLESS = $oldHeadless
    if ($held) { $importGate.ReleaseMutex() }
    $importGate.Dispose()
}
