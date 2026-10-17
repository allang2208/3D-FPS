$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskProject='D:/FPS3D/FPSGAME'
$taskResults=@()
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    $taskPrior=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
    foreach($taskBuild in $taskPrior) {
        Write-Output "Waiting for existing UnrealBuildTool PID $($taskBuild.ProcessId)"
        try {[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()} catch [ArgumentException] {}
    }
    $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('\','/') -like "*$taskProject/FPSGAME.uproject*" })
    if($taskEditors.Count){throw 'Project binaries are occupied; retain source and assets without closing the editor'}
    $taskLog=Join-Path $taskRoot "Receipts/build-$taskTarget.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> (Join-Path $taskRoot "Receipts/build-$taskTarget-stdout.log")
    $taskCode=$LASTEXITCODE
    $taskResults+=@{target=$taskTarget;exit_code=$taskCode;log=$taskLog;finished_utc=[DateTimeOffset]::UtcNow.ToString('o')}
    @{results=$taskResults;game_run=$false;tests_run=$false}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $taskRoot 'Receipts/native-integration-build.json') -Encoding utf8
    Write-Output "$taskTarget BUILD_EXIT=$taskCode"
    if($taskCode -ne 0){Get-Content -LiteralPath $taskLog -Tail 24;throw "Required build failed for $taskTarget"}
}
Write-Output 'Editor and Game builds saved; no editor or game launch.'
