param()
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$engineExe = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$scriptFile = Join-Path $PSScriptRoot 'install.py'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$active = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='FPSGAME.exe'" |
    Where-Object { $_.CommandLine -like '*FPSGAME*' -or -not $_.CommandLine }
$editor = $active | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(^|\s)-game(\s|$)' }
if ($editor -and $active.Count -eq 1) {
    & (Join-Path $projectRoot 'Tools\AssetPipeline\mcp_call_codex.ps1') -PythonScript $scriptFile `
        -OutputFile (Join-Path $PSScriptRoot ("install-bridge-$stamp.txt")) -MaxOutputChars 2500
    exit $LASTEXITCODE
}
if ($active) { Write-Output 'PKM_ASSET_WRITE_DEFERRED_ACTIVE_PROJECT_PROCESS'; exit 75 }
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous asset batch stopped unexpectedly; no write sent.' }
    if (-not $held) { Write-Output 'PKM_ASSET_BATCH_BUSY'; exit 75 }
    $active = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='FPSGAME.exe'" |
        Where-Object { $_.CommandLine -like '*FPSGAME*' -or -not $_.CommandLine }
    if ($active) { Write-Output 'PKM_ASSET_WRITE_DEFERRED_ACTIVE_PROJECT_PROCESS'; exit 75 }
    $log = Join-Path $PSScriptRoot ("install-$stamp.log")
    & $engineExe (Join-Path $projectRoot 'FPSGAME.uproject') -run=pythonscript ("-script=" + $scriptFile) `
        -unattended -nop4 -nosplash -NullRHI -ModelContextProtocolPort=18048 `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' ("-abslog=" + $log) 2>&1 | Select-Object -Last 24
    $code = $LASTEXITCODE
    Write-Output "PKM_INSTALL_EXIT=$code LOG=$log"
    exit $code
}
finally { if ($held) { $gate.ReleaseMutex() }; $gate.Dispose() }
