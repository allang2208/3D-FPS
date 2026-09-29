param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$projectRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot '../../..'))
$importGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
$oldHeadless = $env:SPITTER_HEADLESS
try {
    try { $held = $importGate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] {
        $held = $true
        throw 'Previous UE batch ended unexpectedly. No import was sent.'
    }
    if (-not $held) { throw 'UE asset batch is busy. No import was sent.' }
    $openEditors = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and
        ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
    })
    if ($openEditors.Count -gt 0) { throw 'FPSGAME has an active UE process. Preserve it; use the existing bridge or wait for the commandlet.' }
    $env:SPITTER_HEADLESS = '1'
    $exe = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $project = Join-Path $projectRoot 'FPSGAME.uproject'
    $script = Join-Path $taskRoot 'install_attack_d.py'
    $engineLog = Join-Path $taskRoot 'import-headless.log'
    & $exe $project '-run=pythonscript' "-script=$script" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' "-abslog=$engineLog" *> (Join-Path $taskRoot 'import-console.log')
    if ($LASTEXITCODE -ne 0) { throw "Attack D import exited with $LASTEXITCODE. See $engineLog" }
    Get-Content -LiteralPath (Join-Path $taskRoot 'installation.json')
} finally {
    $env:SPITTER_HEADLESS = $oldHeadless
    if ($held) { $importGate.ReleaseMutex() }
    $importGate.Dispose()
}
