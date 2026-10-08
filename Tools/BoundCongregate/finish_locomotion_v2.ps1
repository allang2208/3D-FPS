param([switch]$AssetsOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME'
$bcEngine='E:/Program Files (x86)/UE_5.8'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/LocomotionV2'
function Wait-BCSlot {
    while ($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        if (@($bcProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count) {
            throw 'Editor is running; preserve it and use the current-editor workflow.'
        }
        $bcBusy=@($bcProcesses | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','UnrealEditor-Cmd.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')
        })
        if (-not $bcBusy.Count) { return }
        [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),'Waiting for active build or commandlet to finish.')
        Start-Sleep -Seconds 5
    }
}
try {
    if (-not $AssetsOnly) {
        foreach ($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
            Wait-BCSlot
            [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),('Building '+$bcTarget))
            & (Join-Path $bcEngine 'Engine/Build/BatchFiles/Build.bat') $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> (Join-Path $bcOutput "build-$bcTarget-console.log")
            if ($LASTEXITCODE -ne 0) { throw ('Native build failed: '+$bcTarget) }
        }
    }
    Wait-BCSlot
    [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),'Importing locomotion sequences and saving Blueprint.')
    & (Join-Path $bcEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$bcProject/FPSGAME.uproject" -run=pythonscript "-script=$bcProject/Tools/BoundCongregate/import_locomotion_v2.py" -unattended -nop4 -nosplash -NoSound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' -stdout -FullStdOutLogOutput "-abslog=$bcOutput/import.log" *> (Join-Path $bcOutput 'import-console.log')
    if ($LASTEXITCODE -ne 0) { throw 'Locomotion asset import failed.' }
    [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),'Complete: native binaries, three animation assets and Blueprint saved. No gameplay tests or renders.')
} catch {
    [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),('Stopped: '+$_.Exception.Message))
    throw
}
