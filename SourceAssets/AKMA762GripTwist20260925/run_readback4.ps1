# Import the thumb-lifted (v4) AKM / A762 reload clips through a headless UE commandlet.
$ErrorActionPreference = 'Stop'
$root = 'D:\FPS3D\FPSGAME'
$engine = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$script = Join-Path $PSScriptRoot 'readback4.py'
$log = Join-Path $PSScriptRoot 'ue-readback4.log'

$busy = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" |
    Where-Object { $_.CommandLine -like '*FPSGAME*' -or -not $_.CommandLine }
if ($busy) {
    Write-Output 'EDITOR_BUSY'
    $busy | Select-Object ProcessId, Name, CommandLine | Format-List
    exit 75
}

$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds(120)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'previous bridge call died; state unknown' }
    if (-not $held) { Write-Output 'BRIDGE_BUSY'; exit 75 }
    & $engine $root/FPSGAME.uproject -run=pythonscript "-script=$script" -unattended -nop4 -nosplash `
        -NullRHI -ModelContextProtocolPort=18012 "-abslog=$log" 2>&1 | Select-Object -Last 40
    $code = $LASTEXITCODE
    Write-Output "COMMANDLET_EXIT=$code"
    exit $code
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
