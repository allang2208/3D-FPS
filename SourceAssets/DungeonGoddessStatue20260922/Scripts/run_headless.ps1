param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string]$LogName,
    [int]$MutexWaitSeconds = 900,
    [int]$WaitForFreeEditorSeconds = 0
)
# Headless UE commandlet runner for this case.
#  - refuses to start while any FPSGAME editor/commandlet is alive (project rule: never
#    close another session's editor, and a second -run=pythonscript process would abort
#    during engine init anyway);
#  - takes the same batch mutex the MCP bridge uses (Local\CodexUeMcp-Port-8000) so this
#    offline authoring cannot interleave with an in-editor integration batch.
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
if ($busy -and $WaitForFreeEditorSeconds -gt 0) {
    # Another session's editor is open. Never close it; queue behind it instead.
    Write-Output "[wait] editor(s) busy: $($busy.ProcessId -join ', ') - waiting up to $WaitForFreeEditorSeconds s"
    $deadline = (Get-Date).AddSeconds($WaitForFreeEditorSeconds)
    while ($busy -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 20
        $busy = Get-FpsgameUnreal
    }
    if (-not $busy) { Write-Output "[wait] editor released, continuing" }
}
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
    Write-Output "[run] $Script"
    Write-Output "[log] $log"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $editor $project -run=pythonscript "-script=$Script" -unattended -nop4 -nosplash -nullrhi "-abslog=$log"
    $code = $LASTEXITCODE
    $sw.Stop()
    Write-Output ("[exit] {0} after {1:N1}s" -f $code, $sw.Elapsed.TotalSeconds)

    $markers = Select-String -Path $log -Pattern 'GODDESS_STATUE_|Error:|Fatal error|Assertion failed|Traceback' -ErrorAction SilentlyContinue
    if ($markers) {
        Write-Output "--- markers ---"
        $markers | Select-Object -First 25 | ForEach-Object { $_.Line }
    }
    exit $code
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
