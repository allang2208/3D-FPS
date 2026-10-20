param([string]$ScriptName = 'save_assets.py', [int]$MaxMinutes = 90)
# Waits until this project has no native build or foreign commandlet, then runs run_ue.ps1 once.
# An open FPSGAME editor is fine: run_ue.ps1 then uses the shared editor bridge gate.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$projectPattern = [regex]::Escape($projectRoot.TrimEnd('\')).Replace('\\', '[\\/]') + '[\\/]'
$deadline = (Get-Date).AddMinutes($MaxMinutes)
$reported = $false
while ((Get-Date) -lt $deadline) {
    # With the editor open the write goes through its bridge, so builds do not matter.
    $editor = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match $projectPattern })
    $busy = if ($editor.Count) { @() } else { @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -in @('dotnet.exe','UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match $projectPattern)
    }) }
    if (-not $busy.Count) {
        & (Join-Path $PSScriptRoot 'run_ue.ps1') -ScriptName $ScriptName -QueueWaitSeconds 1800
        return
    }
    if (-not $reported) { Write-Output 'Waiting for the current FPSGAME build or commandlet; no asset write started.'; $reported = $true }
    Start-Sleep -Seconds 30
}
throw 'FPSGAME stayed busy; no asset write started.'
