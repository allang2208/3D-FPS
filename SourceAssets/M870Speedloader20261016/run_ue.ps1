param([string]$ScriptName = 'read_inputs.py', [int]$RequestTimeoutSeconds = 3600, [int]$QueueWaitSeconds = 60)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskScript = Join-Path $PSScriptRoot $ScriptName
# Only this project counts; audit copies elsewhere under D:/FPS3D are separate processes.
$projectPattern = [regex]::Escape($projectRoot.TrimEnd('\')).Replace('\\', '[\\/]') + '[\\/]'
$editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
    [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match $projectPattern
})
if ($editors.Count) {
    # Long asset batches run only with UE closed (user choice 2026-10-16),
    # never through a running editor.
    throw 'UE editor is open; this batch waits until it is closed. Nothing was read or written.'
}

# Asset read/save only. No editor UI, native build, game launch, render or test.
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try {
        for ($attempt = 0; $attempt -lt 10 -and -not $held; $attempt++) {
            $held = $gate.WaitOne(60000)
            if (-not $held) { Write-Output 'Waiting for the existing UE asset batch gate; no asset write started.' }
        }
    }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous UE batch ended unexpectedly; no new asset write started.' }
    if (-not $held) { throw 'UE authoring gate is busy; no asset write started.' }
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and
            ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match $projectPattern)) -or
        # Only Editor-target builds touch the DLL this commandlet loads; Game builds are independent.
        ($_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match $projectPattern -and $_.CommandLine -match 'FPSGAMEEditor') -or
        ($_.Name -in @('cl.exe','link.exe') -and $_.CommandLine -match $projectPattern -and $_.CommandLine -match '[\\/]UnrealEditor[\\/]')
    })
    if ($busy.Count) { throw 'An editor or native build became active; no commandlet started.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $log = Join-Path $PSScriptRoot "commandlet-$stamp.log"
    $console = Join-Path $PSScriptRoot "commandlet-console-$stamp.log"
    $oldSkipSdk = $env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP = '1'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$log" *> $console
        if ($LASTEXITCODE -ne 0) { throw "Commandlet failed; see $log" }
    } finally { $env:UE_SKIP_UBT_SDK_SETUP = $oldSkipSdk }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
