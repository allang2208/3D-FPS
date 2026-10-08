param([switch]$AssetsOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME';$bcEngine='E:/Program Files (x86)/UE_5.8'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/FullWhipV10'
New-Item -ItemType Directory -Path $bcOutput -Force | Out-Null
function Wait-BCClothV10Slot {
    while($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        if(@($bcProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Editor is open; preserve it. Native replacement and blueprint save need a free background slot.'}
        $bcBusy=@($bcProcesses | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')})
        if(!$bcBusy.Count){return}
        Start-Sleep -Seconds 5
    }
}
if(!$AssetsOnly) {
    foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
        Wait-BCClothV10Slot
        & (Join-Path $bcEngine 'Engine/Build/BatchFiles/Build.bat') $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> (Join-Path $bcOutput "build-$bcTarget-console.log")
        if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget"}
    }
}
Wait-BCClothV10Slot
& (Join-Path $bcEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/import_full_whip_v10.py" -unattended -nop4 -nosplash -NoSound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/save.log" *> (Join-Path $bcOutput 'save-console.log')
if($LASTEXITCODE -ne 0){throw "V10 cloth and cooldown save failed ($LASTEXITCODE); see save.log."}
Write-Output 'Full appendage V10 compiled and saved. No game or tests launched.'
