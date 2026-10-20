param([int]$MaxWaitMinutes = 240, [switch]$SkipEditorBuild)
# Sequential delivery for the V9 M4 sample: Editor build -> asset install (commandlet) -> Game build.
# Never interrupts other sessions: each step waits until no foreign build / commandlet / editor is active.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
function Wait-Idle {
    $said = $false
    while ($true) {
        $busy = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe','UnrealEditor.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if (-not $busy.Count) { return }
        if ((Get-Date) -gt $deadline) { throw 'Other UE work stayed active past the wait limit; nothing further started.' }
        if (-not $said) { Write-Output ("Waiting for other UE work: " + (($busy | ForEach-Object Name) -join ', ')); $said = $true }
        Start-Sleep -Seconds 20
    }
}
if (-not $SkipEditorBuild) {
    Wait-Idle
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'build_native.ps1') -Targets FPSGAMEEditor
    if ($LASTEXITCODE -ne 0) { throw 'Editor build failed' }
}
while ($true) {
    Wait-Idle
    $start = Get-Date
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'run_ue.ps1') -ScriptName install_m4.py
    $log = Get-ChildItem $here -Filter 'commandlet-2*.log' | Where-Object { $_.LastWriteTime -ge $start } | Sort-Object LastWriteTime | Select-Object -Last 1
    if ($log) {
        # A commandlet actually ran: it either completed or failed; never retry a partial write blindly.
        if (Select-String -Path $log.FullName -Pattern 'M4V9_INSTALL_COMPLETE' -Quiet) { break }
        throw "Install commandlet did not complete; see $($log.FullName)"
    }
    if ((Get-Date) -gt $deadline) { throw 'Install could not start before the wait limit.' }
    Start-Sleep -Seconds 30
}
Wait-Idle
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'build_native.ps1') -Targets FPSGAME
if ($LASTEXITCODE -ne 0) { throw 'Game build failed' }
Write-Output 'M4V9_RUN_ALL_COMPLETE'
