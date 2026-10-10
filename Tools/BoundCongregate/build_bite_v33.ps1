$ErrorActionPreference='Stop'
. "$PSScriptRoot/build_review_v31.ps1" -AssetsOnly
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/BiteV33'
foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
    Wait-BCBuildWindow
    Write-Output "Building $bcTarget for M-88 bite V33"
    & "$bcEngine/Build/BatchFiles/Build.bat" $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> "$bcOutput/build-$bcTarget-console.log"
    if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget. See V33 log."}
    Write-Output "Built $bcTarget"
}
Wait-BCBuildWindow
Write-Output 'Saving M-88 bite V33 Blueprint tuning'
& "$bcEngine/Binaries/Win64/UnrealEditor-Cmd.exe" "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/save_bite_v33.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$bcOutput/save.log" *> "$bcOutput/save-console.log"
if($LASTEXITCODE -ne 0){throw 'Blueprint save failed. See V33 save log.'}
