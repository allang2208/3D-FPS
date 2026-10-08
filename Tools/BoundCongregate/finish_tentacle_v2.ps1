param([switch]$AssetsOnly,[switch]$ReviewOnly,[switch]$NativeOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME';$bcEngine='E:/Program Files (x86)/UE_5.8'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/TentacleRepairV2'
function Wait-BCTentacleV2Slot {
    while($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        if(@($bcProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Editor is open; retain it and request user closure for native rebuild.'}
        $bcBusy=@($bcProcesses | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')})
        if(!$bcBusy.Count){return}
        Start-Sleep -Seconds 5
    }
}
if(!$AssetsOnly -and !$ReviewOnly) {
    foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
        Wait-BCTentacleV2Slot
        & (Join-Path $bcEngine 'Engine/Build/BatchFiles/Build.bat') $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> (Join-Path $bcOutput "build-$bcTarget-console.log")
        if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget"}
    }
}
if(!$ReviewOnly -and !$NativeOnly) {
    Wait-BCTentacleV2Slot
    & (Join-Path $bcEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/import_tentacle_v2.py" -unattended -nop4 -nosplash -NoSound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/import.log" *> (Join-Path $bcOutput 'import-console.log')
    if($LASTEXITCODE -ne 0){throw 'Import failed; see import.log.'}
}
Wait-BCTentacleV2Slot
& (Join-Path $bcEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$bcProject/FPSGAME.uproject" -run=BoundCongregateRigReview -TentacleOnly -unattended -nop4 -nosplash -NoSound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/deformation-review.log" *> (Join-Path $bcOutput 'deformation-review-console.log')
if($LASTEXITCODE -ne 0){throw 'Requested deformation review failed; see its report.'}
Write-Output 'Tentacle V2 built, imported, saved; requested isolated deformation review complete. No editor window or game launched.'
