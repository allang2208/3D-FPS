$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(60))
    if (-not $held) { throw 'UE asset batch is busy; no commandlet started.' }
    $running=Get-CimInstance Win32_Process -Filter "name='UnrealEditor.exe' OR name='UnrealEditor-Cmd.exe'"
    if ($running) { throw 'UE is running; use the existing editor bridge instead.' }
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=pythonscript' "-script=$taskRoot/integrate.py" '-unattended' '-AllowCommandletRendering' '-RenderOffscreen' '-NoSound' '-nosplash' '-nop4' '-UTF8Output' '-stdout' '-FullStdOutLogOutput' "-abslog=$taskRoot/commandlet-$stamp.log" *> "$taskRoot/console-$stamp.log"
    exit $LASTEXITCODE
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
