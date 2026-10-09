$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskOutput = Join-Path $taskRoot 'SourceAssets/FacelessResearcher20261009/V05'
$taskResults = @()
foreach ($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    $taskPriorBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
    foreach ($taskPriorBuild in $taskPriorBuilds) {
        try { [Diagnostics.Process]::GetProcessById($taskPriorBuild.ProcessId).WaitForExit() } catch [ArgumentException] { }
    }
    $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskRoot/FPSGAME.uproject") })
    if ($taskEditors.Count -gt 0) { throw 'FPSGAME binaries are now occupied. Researcher assets remain saved; native entry build deferred.' }
    $taskLog = Join-Path $taskOutput ("Logs/build-" + $taskTarget + ".log")
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> (Join-Path $taskOutput ("Logs/build-" + $taskTarget + "-stdout.log"))
    $taskCode = $LASTEXITCODE
    $taskResults += @{ target=$taskTarget; exit_code=$taskCode; log=$taskLog }
    $taskReceipt = @{ results=$taskResults; tested=$false } | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText((Join-Path $taskOutput 'build_receipt.json'), $taskReceipt, [Text.UTF8Encoding]::new($false))
    if ($taskCode -ne 0) { throw "Required build failed for $taskTarget. See $taskLog" }
}
Write-Output 'Researcher state transitions built for Editor and Game. No editor or game started.'
