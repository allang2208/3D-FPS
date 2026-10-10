param([switch]$AssetsOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME'
$bcEngine='E:/Program Files (x86)/UE_5.8/Engine'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/GarmentDrapeV24'
function Wait-BCBuildWindow {
    $bcNotice=$false
    while($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        $bcGui=$bcProcesses | Where-Object { $_.Name -eq 'UnrealEditor.exe' }
        if($bcGui) { throw 'A running editor must retain its loaded assets. Resume V24 using the editor bridge.' }
        $bcBusy=$bcProcesses | Where-Object {
            $_.Name -match '^(UnrealEditor-Cmd|FPSGAME.*|cl|link|UnrealBuildTool)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        $bcLocked=$false
        $bcDll=Join-Path $bcProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        if(Test-Path -LiteralPath $bcDll) {
            try { $bcStream=[IO.File]::Open($bcDll,'Open','ReadWrite','None'); $bcStream.Dispose() }
            catch { $bcLocked=$true }
        }
        if(!$bcBusy -and !$bcLocked) { return }
        if(!$bcNotice) { Write-Output 'Waiting for the current native build/asset process to release the build window.'; $bcNotice=$true }
        Start-Sleep -Seconds 10
    }
}
if(!$AssetsOnly) {
    foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
        Wait-BCBuildWindow
        Write-Output "Building $bcTarget for V24"
        & "$bcEngine/Build/BatchFiles/Build.bat" $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> "$bcOutput/build-$bcTarget-console.log"
        if($LASTEXITCODE -ne 0) { throw "Build failed: $bcTarget. See the V24 build log." }
        Write-Output "Built $bcTarget"
    }
}
Wait-BCBuildWindow
Write-Output 'Importing V24 mesh, fabric, clothing and matched continuous corpse; saving original monster visual.'
& "$bcEngine/Binaries/Win64/UnrealEditor-Cmd.exe" "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/import_garment_v24.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOutput/import-final.log" *> "$bcOutput/import-final-console.log"
$bcImportExit=$LASTEXITCODE
if(Test-Path -LiteralPath "$bcOutput/delivery.json") {
    $bcDelivery=Get-Content -LiteralPath "$bcOutput/delivery.json" -Raw | ConvertFrom-Json
    if($bcDelivery.saved) {
        Write-Output "V24 assets and blueprint saved. Commandlet exit code: $bcImportExit"
        if($bcImportExit -ne 0) { Write-Output 'Commandlet exit was abnormal after save; retain the logs and saved receipt.' }
        exit 0
    }
}
throw "V24 save did not finish. Commandlet exit: $bcImportExit"
