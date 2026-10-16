$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$receipt=Join-Path $project 'SourceAssets/PotionWorkbenchDesign20261015/EntryV12'
$builder='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
function Wait-ExistingBuild {
    $last=''
    while($true) {
        $running=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*' })
        if($running.Count -eq 0){return}
        $ids=($running.ProcessId -join ',')
        if($ids -ne $last){Write-Output "Waiting for existing UBT process: $ids"; $last=$ids}
        foreach($process in $running){Wait-Process -Id $process.ProcessId -Timeout 30 -ErrorAction SilentlyContinue}
    }
}
Wait-ExistingBuild
Write-Output 'Building final Game target'
& $builder FPSGAME Win64 Development "-Project=$project/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=3 "-Log=$receipt/build-game-accepted.log" *> "$receipt/build-game-accepted-console.log"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Wait-ExistingBuild
# Never close a running editor or overwrite a module that it has loaded.
foreach($editor in @(Get-Process UnrealEditor -ErrorAction SilentlyContinue)) {
    $loaded=@($editor.Modules | Where-Object { $_.FileName -like 'D:\FPS3D\FPSGAME\Binaries\Win64\*FPSGAME*.dll' })
    if($loaded.Count -gt 0){Write-Output "EDITOR_MODULE_OCCUPIED PID $($editor.Id)";exit 73}
}
Write-Output 'Building final Editor target'
& $builder FPSGAMEEditor Win64 Development "-Project=$project/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=3 "-Log=$receipt/build-editor.log" *> "$receipt/build-editor-console.log"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Output 'ALCHEMY_ENTRY_V12_GAME_EDITOR_BUILT'
exit $LASTEXITCODE
