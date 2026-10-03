param([int]$WaitForBuildPid = 0, [ValidateSet('FPSGAMEEditor','FPSGAME')][string]$TargetName = 'FPSGAMEEditor')
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
if ($WaitForBuildPid -gt 0) {
    try {
        $taskBuildProcess = [Diagnostics.Process]::GetProcessById($WaitForBuildPid)
        Write-Output 'Waiting for the already-running build process to exit before submitting M07.'
        $taskBuildProcess.WaitForExit()
    } catch [ArgumentException] { }
}
$taskOtherBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
foreach ($taskOtherBuild in $taskOtherBuilds) {
    try { [Diagnostics.Process]::GetProcessById($taskOtherBuild.ProcessId).WaitForExit() } catch [ArgumentException] { }
}
$taskCommands = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine.Replace('\','/').IndexOf("$taskRoot/FPSGAME.uproject",[StringComparison]::OrdinalIgnoreCase) -ge 0 })
foreach ($taskCommand in $taskCommands) {
    Write-Output 'Waiting for an existing FPSGAME background asset command to release the native binaries.'
    try { [Diagnostics.Process]::GetProcessById($taskCommand.ProcessId).WaitForExit() } catch [ArgumentException] { }
}
if ($TargetName -eq 'FPSGAMEEditor') {
    while ($true) {
        $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine.Replace('\','/').IndexOf("$taskRoot/FPSGAME.uproject",[StringComparison]::OrdinalIgnoreCase) -ge 0 })
        $taskInteractiveEditors = @($taskEditors | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)' })
        if ($taskInteractiveEditors.Count -gt 0) { throw 'An editor process is running; binaries were left intact. M07 background build is deferred.' }
        if ($taskEditors.Count -eq 0) { break }
        Write-Output 'Waiting for background FPSGAME command/game processes to release the Editor module naturally.'
        foreach ($taskEditor in $taskEditors) {
            try { [Diagnostics.Process]::GetProcessById($taskEditor.ProcessId).WaitForExit() } catch [ArgumentException] { }
        }
    }
} else {
    $taskGameExecutables = @(Get-CimInstance Win32_Process -Filter "Name='FPSGAME.exe'" | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.Replace('\','/').StartsWith($taskRoot, [StringComparison]::OrdinalIgnoreCase) })
    if ($taskGameExecutables.Count -gt 0) { throw 'The target game binary is in use; M07 background build is deferred.' }
}
$taskLog = Join-Path $taskRoot ('Saved/BuildEditor/m07-' + $TargetName + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $TargetName Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -MaxParallelActions=4 -WaitMutex "-Log=$taskLog"
if ($LASTEXITCODE -ne 0) { throw "M07 required Editor build failed: $taskLog" }
Write-Output "M07 authoring binaries built: $taskLog"
