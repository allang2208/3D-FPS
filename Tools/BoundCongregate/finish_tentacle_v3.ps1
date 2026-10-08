param([switch]$AssetsOnly,[switch]$NativeOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME';$bcEngine='E:/Program Files (x86)/UE_5.8'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV3'
function Wait-BCTentacleV3Slot {
    while($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        if(@($bcProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Editor is open; preserve it. Background replacement requires user closure.'}
        $bcBusy=@($bcProcesses | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')})
        if(!$bcBusy.Count){return}
        Start-Sleep -Seconds 5
    }
}
if(!$AssetsOnly) {
    foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
        Wait-BCTentacleV3Slot
        & (Join-Path $bcEngine 'Engine/Build/BatchFiles/Build.bat') $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> (Join-Path $bcOutput "build-$bcTarget-console.log")
        if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget"}
    }
}
if(!$NativeOnly) {
    Wait-BCTentacleV3Slot
    & (Join-Path $bcEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/import_tentacle_v3.py" -unattended -nop4 -nosplash -NoSound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/import.log" *> (Join-Path $bcOutput 'import-console.log')
    if($LASTEXITCODE -ne 0){throw 'Import failed; see import.log.'}
}
Write-Output 'Tentacle V3 build/save operations complete. No game, review or editor window launched.'
