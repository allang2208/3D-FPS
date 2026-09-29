param([ValidateSet('retarget_attacks','install_attacks')][string]$Stage = 'retarget_attacks')
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$projectRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot '../../..'))
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
$oldHeadless = $env:SPITTER_HEADLESS
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous UE batch ended unexpectedly; no request sent.' }
    if (-not $held) { throw 'UE batch is busy; no request sent.' }
    $active = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and
        ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
    })
    if ($active.Count) { throw 'Preserving the active FPSGAME process; use its bridge or wait for the commandlet.' }
    $env:SPITTER_HEADLESS = '1'
    $project = Join-Path $projectRoot 'FPSGAME.uproject'
    $script = Join-Path $taskRoot ($Stage+'.py')
    $log = Join-Path $taskRoot ($Stage+'-ue.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $project '-run=pythonscript' "-script=$script" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' "-abslog=$log" *> (Join-Path $taskRoot ($Stage+'-console.log'))
    if ($LASTEXITCODE -ne 0) { throw "Commandlet exited $LASTEXITCODE; see $log" }
    Get-Content -LiteralPath (Join-Path $taskRoot $(if ($Stage -eq 'retarget_attacks') { 'native.json' } else { 'installation.json' }))
} finally {
    $env:SPITTER_HEADLESS = $oldHeadless
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
