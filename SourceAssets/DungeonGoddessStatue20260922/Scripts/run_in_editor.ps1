param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(Mandatory = $true)][string]$LogName,
    [int]$WaitForEditorSeconds = 900,
    [int]$MutexWaitSeconds = 900
)
# Runs a case script inside the *already open* FPSGAME editor over the Python
# remote-execution socket (Config/DefaultEngine.ini: bRemoteExecution=True).
# Used instead of a headless commandlet whenever an editor is running - a second
# UnrealEditor-Cmd would abort during engine init, and the project forbids closing
# another session's editor.
#
# Takes the same batch mutex as the MCP bridge (Local\CodexUeMcp-Port-8000) so the
# import/install batch cannot interleave with another session's integration batch.
$ErrorActionPreference = 'Stop'
$case = Split-Path -Parent $PSScriptRoot
$exec = 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\ue_python_exec.py'
$log = Join-Path $case ('Logs\' + $LogName)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null

function Test-EditorReady {
    # ue_python_exec writes its failure to stderr; with ErrorActionPreference=Stop a
    # native non-zero exit would otherwise abort this polling loop.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & python $exec --list 2>$null | Out-String
        return ($LASTEXITCODE -eq 0) -and ($out -match 'FPSGAME')
    }
    finally { $ErrorActionPreference = $prev }
}

$deadline = (Get-Date).AddSeconds($WaitForEditorSeconds)
while (-not (Test-EditorReady)) {
    if ((Get-Date) -gt $deadline) {
        throw "No FPSGAME editor node after $WaitForEditorSeconds s (is the editor still loading, or remote execution off?)."
    }
    Start-Sleep -Seconds 15
}
$nodes = & python $exec --list 2>&1
Write-Output "[node] $nodes"

$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromMilliseconds($MutexWaitSeconds * 1000)) }
    catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw "Batch mutex still held after $MutexWaitSeconds s; nothing was run." }

    Write-Output "[run] $Script"
    $out = & python $exec --script $Script 2>&1
    $code = $LASTEXITCODE
    $out | Set-Content -Path $log -Encoding UTF8
    $out | Select-Object -First 60
    Write-Output "[exit] $code   [log] $log"
    exit $code
}
finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
