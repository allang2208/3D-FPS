param([switch]$AssetsOnly,[switch]$ReviewOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME';$bcEngine='E:/Program Files (x86)/UE_5.8'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/RigRepairV3'
function Wait-BCSlot {
    while ($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        if (@($bcProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count) { throw 'Editor remains open; preserve it. User must save and close before the full native build.' }
        $bcBusy=@($bcProcesses | Where-Object {$_.Name -in @('UnrealBuildTool.exe','UnrealEditor-Cmd.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')})
        if (-not $bcBusy.Count) { return }
        [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),'Waiting for active build or commandlet.')
        Start-Sleep -Seconds 5
    }
}
function Run-BCCommandlet([string]$bcName,[string]$bcScript,[string]$bcLog) {
    Wait-BCSlot
    $bcArguments=@("$bcProject/FPSGAME.uproject","-run=$bcName",'-unattended','-nop4','-nosplash','-NoSound','-AllowCommandletRendering','-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0','-stdout','-FullStdOutLogOutput',"-abslog=$bcOutput/$bcLog.log")
    if($bcScript){$bcArguments+= "-script=$bcProject/$bcScript"}
    & (Join-Path $bcEngine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') @bcArguments *> (Join-Path $bcOutput "$bcLog-console.log")
    if($LASTEXITCODE -ne 0){throw "$bcName failed; see $bcLog.log"}
}
try {
    if(-not $AssetsOnly -and -not $ReviewOnly) {
        foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
            Wait-BCSlot
            [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),"Building $bcTarget")
            & (Join-Path $bcEngine 'Engine/Build/BatchFiles/Build.bat') $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> (Join-Path $bcOutput "build-$bcTarget-console.log")
            if($LASTEXITCODE -ne 0){throw "Native build failed: $bcTarget"}
        }
    }
    if(-not $ReviewOnly) {
        [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),'Importing repaired mesh, cloth, seven clips and matching continuous corpse.')
        Run-BCCommandlet 'pythonscript' 'Tools/BoundCongregate/import_rig_v3.py' 'import'
    }
    [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),'Running the user-requested compressed clip and isolated rig reviews.')
    Run-BCCommandlet 'pythonscript' 'Tools/BoundCongregate/audit_ue_clips_v3.py' 'compressed-clips'
    Run-BCCommandlet 'BoundCongregateRigReview' '' 'runtime-rig-review'
    [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),'Complete: saved production assets, native binaries and requested isolated rig checks. No editor or game launched.')
} catch {
    [IO.File]::WriteAllText((Join-Path $bcOutput 'stage.txt'),('Stopped: '+$_.Exception.Message));throw
}
