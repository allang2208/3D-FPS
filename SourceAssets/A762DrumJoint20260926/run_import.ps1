param([switch]$StageOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$engineExe = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous asset batch ended unexpectedly; no import was sent.' }
    if (-not $held) { Write-Output 'ASSET_BATCH_BUSY'; exit 75 }
    if (-not $StageOnly) {
        $projectProcesses = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" |
            Where-Object { $_.CommandLine -like '*FPSGAME*' -or -not $_.CommandLine }
        if ($projectProcesses) {
            Write-Output 'LIVE_PROJECT_ASSET_WRITE_DEFERRED'
            $projectProcesses | Select-Object ProcessId, Name, CommandLine | Format-List
            exit 75
        }
    }
    $env:A762_DRUM_STAGE_ONLY = if ($StageOnly) { '1' } else { '0' }
    $stageName = if ($StageOnly) { 'candidate' } else { 'install' }
    $log = Join-Path $PSScriptRoot ($stageName + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
    & $engineExe (Join-Path $projectRoot 'FPSGAME.uproject') -run=pythonscript `
        ("-script=" + (Join-Path $PSScriptRoot 'install.py')) -unattended -nop4 -nosplash -NullRHI `
        -ModelContextProtocolPort=18026 ("-abslog=" + $log) 2>&1 | Select-Object -Last 35
    $code = $LASTEXITCODE
    Write-Output "COMMANDLET_EXIT=$code LOG=$log"
    exit $code
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
