param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string]$LogName,
    [int]$MutexWaitSeconds = 900
)
# Headless UE commandlet runner for the dark-bow case (ASCII only on purpose).
#  - refuses to start while any FPSGAME editor/commandlet is alive: never close another
#    session's editor, and a second -run=pythonscript would abort during engine init anyway;
#  - takes the same batch mutex the MCP bridge uses so offline authoring cannot interleave
#    with an in-editor integration batch.
$ErrorActionPreference = 'Stop'
$case = Split-Path -Parent $PSScriptRoot
$project = 'D:/FPS3D/FPSGAME/FPSGAME.uproject'
$editor = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$log = Join-Path $case ('Logs\' + $LogName)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null

function Get-FpsgameUnreal {
    Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" -ErrorAction SilentlyContinue |
        Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME' }
}

$busy = Get-FpsgameUnreal
if ($busy) {
    $busy | Select-Object ProcessId, CreationDate, @{n = 'cmd'; e = { $_.CommandLine } } | Format-List
    throw "Another FPSGAME Unreal process is running ($($busy.ProcessId -join ', ')); refusing to start a second one."
}

$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($MutexWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw "Batch mutex still held after $MutexWaitSeconds s; nothing was run." }

    if (Test-Path $log) { Remove-Item $log -Force }
    # The commandlet resolves a relative -script against the engine's own Binaries/Win64
    # working directory, so always hand it an absolute path.
    $scriptFull = (Resolve-Path -LiteralPath $Script).Path.Replace('\', '/')
    Write-Output "[run] $scriptFull"
    Write-Output "[log] $log"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $editor $project -run=pythonscript "-script=$scriptFull" -unattended -nop4 -nosplash -nullrhi "-abslog=$log"
    $code = $LASTEXITCODE
    $sw.Stop()
    Write-Output ("[exit] {0} after {1:N1}s" -f $code, $sw.Elapsed.TotalSeconds)

    $markers = Select-String -Path $log -Pattern 'DARKBOW_|Error:|Fatal error|Assertion failed|Traceback' -ErrorAction SilentlyContinue
    if ($markers) {
        Write-Output '--- markers ---'
        $markers | Select-Object -First 40 | ForEach-Object { $_.Line }
    }
    exit $code
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
