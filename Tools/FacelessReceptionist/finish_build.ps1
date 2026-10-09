$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskOutput = Join-Path $taskRoot 'SourceAssets/FacelessReceptionist20261007'
$taskPriorBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
foreach ($taskPriorBuild in $taskPriorBuilds) {
    try { [Diagnostics.Process]::GetProcessById($taskPriorBuild.ProcessId).WaitForExit() } catch [ArgumentException] { }
}
$taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskRoot/FPSGAME.uproject") })
if ($taskEditors.Count -gt 0) { throw 'An FPSGAME editor/commandlet now holds the binaries. The receptionist assets remain saved; build deferred.' }
$taskCpp = Join-Path $taskRoot 'Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp'
$taskSource = [IO.File]::ReadAllText($taskCpp)
$taskAnchor = '    Add(TEXT("NurseZombie"), TEXT("护士僵尸"), TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"), 44.f);'
$taskLine = '    Add(TEXT("FacelessReceptionist"), TEXT("无面接待员"), TEXT("/Game/Monsters/FacelessReceptionist/BP_FacelessReceptionist.BP_FacelessReceptionist_C"), 44.f);'
if (-not $taskSource.Contains('TEXT("FacelessReceptionist")')) {
    if (-not $taskSource.Contains($taskAnchor)) { throw 'The scoped insertion anchor changed; no source overwritten.' }
    $taskSource = $taskSource.Replace($taskAnchor, $taskAnchor + [Environment]::NewLine + $taskLine)
    [IO.File]::WriteAllText($taskCpp, $taskSource, [Text.UTF8Encoding]::new($false))
}
$taskResults = @()
foreach ($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    $taskOtherBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
    foreach ($taskOtherBuild in $taskOtherBuilds) {
        try { [Diagnostics.Process]::GetProcessById($taskOtherBuild.ProcessId).WaitForExit() } catch [ArgumentException] { }
    }
    $taskLog = Join-Path $taskOutput ("Logs/build-" + $taskTarget + ".log")
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> (Join-Path $taskOutput ("Logs/build-" + $taskTarget + "-stdout.log"))
    $taskResults += @{ target=$taskTarget; exit_code=$LASTEXITCODE; log=$taskLog }
    @{ results=$taskResults; tested=$false } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskOutput 'build_receipt.json') -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw "Required build failed for $taskTarget. See $taskLog" }
}
Write-Output 'Receptionist F6 entry and both native targets built. No application or game started.'
