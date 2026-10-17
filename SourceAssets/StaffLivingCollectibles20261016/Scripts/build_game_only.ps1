$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskProject='D:/FPS3D/FPSGAME'
$taskPrior=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object CommandLine -match 'UnrealBuildTool')
foreach($taskBuild in $taskPrior) {
    Write-Output "Waiting for existing UnrealBuildTool PID $($taskBuild.ProcessId)"
    try {[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()} catch [ArgumentException] {}
}
$taskLog=Join-Path $taskRoot 'Receipts/build-FPSGAME.log'
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> (Join-Path $taskRoot 'Receipts/build-FPSGAME-stdout.log')
$taskCode=$LASTEXITCODE
@{target='FPSGAME';exit_code=$taskCode;log=$taskLog;finished_utc=[DateTimeOffset]::UtcNow.ToString('o');tests_run=$false;game_run=$false}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $taskRoot 'Receipts/native-game-build.json') -Encoding utf8
Write-Output "FPSGAME BUILD_EXIT=$taskCode"
if($taskCode -ne 0){Get-Content -LiteralPath $taskLog -Tail 28;throw 'Game target build failed'}
