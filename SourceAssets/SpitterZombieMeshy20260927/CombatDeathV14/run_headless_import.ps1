$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$projectRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot '../../..'))
$build = Get-Content -LiteralPath (Join-Path $taskRoot 'build-result.json') -Raw | ConvertFrom-Json
if ($build.exit_code -ne 0) { throw 'Complete the V14 native build before final installation.' }
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
$oldHeadless = $env:SPITTER_HEADLESS
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous asset batch ended unexpectedly; no request sent.' }
    if (-not $held) { throw 'UE asset batch is busy; no request sent.' }
    $active = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and
        ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
    })
    if ($active.Count) { throw 'Preserving the active UE process; use the existing editor bridge.' }
    $env:SPITTER_HEADLESS = '1'
    $project = Join-Path $projectRoot 'FPSGAME.uproject'
    $script = Join-Path $taskRoot 'install_combat.py'
    $log = Join-Path $taskRoot 'import-headless.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $project '-run=pythonscript' "-script=$script" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' "-abslog=$log" *> (Join-Path $taskRoot 'import-console.log')
    if ($LASTEXITCODE -ne 0) { throw "Combat import exited $LASTEXITCODE; see $log" }
    Get-Content -LiteralPath (Join-Path $taskRoot 'installation.json')
} finally {
    $env:SPITTER_HEADLESS = $oldHeadless
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
