param([switch]$AssetsOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME'
$bcEngine='E:/Program Files (x86)/UE_5.8'
$bcOut=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/TentacleAttackV1'
[IO.Directory]::CreateDirectory($bcOut) | Out-Null
function Wait-BCTentacleSlot {
    while($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        if(@($bcProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count) {
            throw 'Editor is running; retain it and ask the current user to save/close before native rebuild.'
        }
        $bcBusy=@($bcProcesses | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')})
        if(!$bcBusy.Count){return}
        Start-Sleep -Seconds 5
    }
}
if(!$AssetsOnly) {
    foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
        Wait-BCTentacleSlot
        & (Join-Path $bcEngine 'Engine/Build/BatchFiles/Build.bat') $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOut/build-$bcTarget-complete.log" *> (Join-Path $bcOut "build-$bcTarget-complete-console.log")
        if($LASTEXITCODE -ne 0){throw "Build failed: $bcTarget. See its build log."}
    }
}
Wait-BCTentacleSlot
& (Join-Path $bcEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/install_tentacle_attack_v1.py" -unattended -nop4 -nosplash -NoSound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$bcOut/install.log" *> (Join-Path $bcOut 'install-console.log')
if($LASTEXITCODE -ne 0){throw 'Blueprint install failed; see install.log.'}
Write-Output 'Tentacle attack built and saved. No game, GUI editor, or tests launched.'
