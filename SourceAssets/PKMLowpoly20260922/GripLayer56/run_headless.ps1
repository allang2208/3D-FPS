param([string]$Script = 'install.py', [int]$WaitMinutes = 20)
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    $held = $gate.WaitOne([TimeSpan]::FromMinutes($WaitMinutes))
    if (-not $held) { throw 'UE asset batch is busy; no commandlet started.' }
    # The FPSGAME-mp copy is a separate project (multiplayer tests); it never loads these packages.
    $running = Get-CimInstance Win32_Process -Filter "name='UnrealEditor.exe' OR name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -notmatch 'FPSGAME-mp' }
    if ($running) { throw 'UE is running; state preserved, no commandlet started.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $env:GRIPLAYER56_HEADLESS = '1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=pythonscript' "-script=$taskRoot/$Script" '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$taskRoot/commandlet-$stamp.log" *> "$taskRoot/console-$stamp.log"
    Write-Output "exit=$LASTEXITCODE log=$taskRoot/commandlet-$stamp.log"
    exit $LASTEXITCODE
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
