$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME'
$bcEngine='E:/Program Files (x86)/UE_5.8/Engine'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/MeleeV17'
function Require-BCIdle {
    $bcBusy=Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor|^FPSGAME|^UnrealBuildTool' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }
    if($bcBusy){throw 'A UE editor, game, commandlet or native build is active; preserve it and resume after it finishes.'}
}
foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
    Require-BCIdle
    Write-Output "Building $bcTarget"
    & "$bcEngine/Build/BatchFiles/Build.bat" $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -gather -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget-ready.log" *> "$bcOutput/build-$bcTarget-console.log"
    if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget; see $bcOutput/build-$bcTarget-ready.log"}
    Write-Output "Built $bcTarget"
}
Require-BCIdle
Write-Output 'Saving melee animations and current monster blueprint'
& "$bcEngine/Binaries/Win64/UnrealEditor-Cmd.exe" "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/import_melee_v17.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/import-final.log" *> "$bcOutput/import-final-console.log"
if($LASTEXITCODE -ne 0){throw "Import process failed; see $bcOutput/import-final.log"}
$bcDelivery=Get-Content "$bcOutput/delivery.json" -Raw | ConvertFrom-Json
if(-not $bcDelivery.saved){throw 'Import did not report saved assets.'}
Write-Output 'MELEE_V17_BUILT_AND_SAVED; no game or tests launched'
