$ErrorActionPreference='Stop'
. "$PSScriptRoot/build_review_v31.ps1" -AssetsOnly
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/DeathV34'
New-Item -ItemType Directory -Force $bcOutput | Out-Null
foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
    Wait-BCBuildWindow
    Write-Output "Building $bcTarget for M-88 unsupported death V34"
    & "$bcEngine/Build/BatchFiles/Build.bat" $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> "$bcOutput/build-$bcTarget-console.log"
    if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget. See V34 log."}
    Write-Output "Built $bcTarget"
}
Wait-BCBuildWindow
Write-Output 'Saving the M-88 unsupported drop profile and live binding'
& "$bcEngine/Binaries/Win64/UnrealEditor-Cmd.exe" "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/install_death_v34.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$bcOutput/install.log" *> "$bcOutput/install-console.log"
if($LASTEXITCODE -ne 0){throw 'Death profile install failed. See V34 install log.'}
