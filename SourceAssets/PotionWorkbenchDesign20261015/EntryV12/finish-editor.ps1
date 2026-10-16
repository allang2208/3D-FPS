$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$receipt=Join-Path $project 'SourceAssets/PotionWorkbenchDesign20261015/EntryV12'
while($true) {
    $running=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*' })
    if($running.Count -eq 0){break}
    foreach($process in $running){Wait-Process -Id $process.ProcessId -Timeout 30 -ErrorAction SilentlyContinue}
}
foreach($editor in @(Get-Process UnrealEditor -ErrorAction SilentlyContinue)) {
    $loaded=@($editor.Modules | Where-Object { $_.FileName -like 'D:\FPS3D\FPSGAME\Binaries\Win64\*FPSGAME*.dll' })
    if($loaded.Count -gt 0){Write-Output "EDITOR_MODULE_OCCUPIED PID $($editor.Id)";exit 73}
}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$project/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=6 "-Log=$receipt/build-editor.log" *> "$receipt/build-editor-console.log"
exit $LASTEXITCODE
