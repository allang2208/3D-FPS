param([ValidateSet('FPSGAMEEditor','FPSGAME')][string[]]$Targets=@('FPSGAMEEditor','FPSGAME'),[switch]$Prepare,[switch]$Install)
$ErrorActionPreference='Stop'
. "$PSScriptRoot/build_review_v31.ps1" -AssetsOnly
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/DeathV32'
foreach($bcTarget in $Targets) {
    Wait-BCBuildWindow
    Write-Output "Building $bcTarget for M-88 V32"
    & "$bcEngine/Build/BatchFiles/Build.bat" $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> "$bcOutput/build-$bcTarget-console.log"
    if($LASTEXITCODE -ne 0) { throw "Build failed: $bcTarget. See the V32 build log." }
    Write-Output "Built $bcTarget"
}
foreach($bcStage in @('prepare','install')) {
    if(($bcStage -eq 'prepare' -and !$Prepare) -or ($bcStage -eq 'install' -and !$Install)){continue}
    Wait-BCBuildWindow
    Write-Output "Saving M-88 V32 assets: $bcStage"
    & "$bcEngine/Binaries/Win64/UnrealEditor-Cmd.exe" "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/${bcStage}_death_v32.py" -unattended -nop4 -nosplash -nosound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/$bcStage.log" *> "$bcOutput/$bcStage-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset $bcStage failed. See the V32 log."}
}
