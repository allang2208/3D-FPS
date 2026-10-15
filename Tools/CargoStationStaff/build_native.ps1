param([string[]]$Targets = @('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskOutput = Join-Path $taskRoot 'SourceAssets/CargoStationStaff20261014/V01'
$taskResults = @()
foreach ($taskTarget in $Targets) {
    $taskPriorBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
    foreach ($taskPriorBuild in $taskPriorBuilds) {
        try { [Diagnostics.Process]::GetProcessById($taskPriorBuild.ProcessId).WaitForExit() } catch [ArgumentException] { }
    }
    $taskBackgroundEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskRoot/FPSGAME.uproject") })
    foreach ($taskBackgroundEditor in $taskBackgroundEditors) {
        try { [Diagnostics.Process]::GetProcessById($taskBackgroundEditor.ProcessId).WaitForExit() } catch [ArgumentException] { }
    }
    $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskRoot/FPSGAME.uproject") })
    if ($taskTarget -eq 'FPSGAMEEditor' -and $taskEditors.Count -gt 0) { throw 'FPSGAME binaries are now occupied. Cargo staff assets remain saved; native entry build deferred.' }
    $taskLog = Join-Path $taskOutput ("Logs/build-" + $taskTarget + ".log")
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> (Join-Path $taskOutput ("Logs/build-" + $taskTarget + "-stdout.log"))
    $taskCode = $LASTEXITCODE
    $taskResults += @{ target=$taskTarget; exit_code=$taskCode; log=$taskLog }
    $taskReceipt = @{ results=$taskResults; tested=$false } | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText((Join-Path $taskOutput 'build_receipt.json'), $taskReceipt, [Text.UTF8Encoding]::new($false))
    if ($taskCode -ne 0) { throw "Required build failed for $taskTarget. See $taskLog" }
}
Write-Output ('Completed targets: ' + ($Targets -join ', ') + '. No editor or game started.')
