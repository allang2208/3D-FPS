param([switch]$AssetsOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME'
$bcEngine='E:/Program Files (x86)/UE_5.8/Engine'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/GarmentDrapeV18'
function Require-BCGarmentSlot {
    $bcActive=Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor|^FPSGAME|^UnrealBuildTool' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }
    if($bcActive){throw 'Preserve the active UE/editor/build process. Resume in a free background slot.'}
}
if(!$AssetsOnly) {
    foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
        Require-BCGarmentSlot
        Write-Output "Building $bcTarget"
        & "$bcEngine/Build/BatchFiles/Build.bat" $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> "$bcOutput/build-$bcTarget-console.log"
        if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget"}
        Write-Output "Built $bcTarget"
    }
}
Require-BCGarmentSlot
Write-Output 'Importing and saving V18 garment, physics and matching corpse'
& "$bcEngine/Binaries/Win64/UnrealEditor-Cmd.exe" "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/import_garment_drape_v18.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/import-final.log" *> "$bcOutput/import-final-console.log"
if($LASTEXITCODE -ne 0){throw 'V18 import/save failed; see import-final.log.'}
$bcDelivery=Get-Content "$bcOutput/delivery.json" -Raw | ConvertFrom-Json
if(!$bcDelivery.saved){throw 'V18 asset save did not complete.'}
Write-Output 'GARMENT_V18_BUILT_AND_SAVED; no game, render or tests launched'
