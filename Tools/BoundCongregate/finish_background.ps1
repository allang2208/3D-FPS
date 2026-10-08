param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8',[switch]$AssetsOnly)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskRecords=Join-Path $taskRoot 'SourceAssets/BoundCongregateMeshy20261006/Records'
$taskState=Join-Path $taskRecords 'background-stage.txt'
function Wait-ForBuildSlot {
    while ($true) {
        $taskProcesses=Get-CimInstance Win32_Process
        $taskActive=@($taskProcesses | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','UnrealEditor-Cmd.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')
        })
        if ($taskActive.Count -eq 0) { break }
        [IO.File]::WriteAllText($taskState,'Waiting for the active native build or commandlet to finish.')
        Start-Sleep -Seconds 5
    }
    $taskEditors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe'})
    if ($taskEditors.Count -gt 0) { throw 'An Unreal editor or commandlet is running. Existing processes were preserved.' }
}
try {
    if (-not $AssetsOnly) { foreach ($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
        Wait-ForBuildSlot
        [IO.File]::WriteAllText($taskState,'Building '+$taskTarget)
        $taskLog=Join-Path $taskRecords ('build-'+$taskTarget+'.log')
        $taskConsole=Join-Path $taskRecords ('build-'+$taskTarget+'-console.log')
        & (Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat') $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> $taskConsole
        if ($LASTEXITCODE -ne 0) { throw ('Build failed: '+$taskTarget+'; '+$taskConsole) }
    } }
    Wait-ForBuildSlot
    [IO.File]::WriteAllText($taskState,'Importing and saving BoundCongregate assets in a background commandlet.')
    $taskImportLog=Join-Path $taskRecords 'import-assets.log'
    & (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/Tools/BoundCongregate/import_assets.py" -unattended -nop4 -nosplash -NoSound -AllowCommandletRendering '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' -stdout -FullStdOutLogOutput "-abslog=$taskImportLog" *> (Join-Path $taskRecords 'import-assets-console.log')
    if ($LASTEXITCODE -ne 0) { throw ('Asset import failed; '+$taskImportLog) }
    $taskDelivery=Get-Content (Join-Path $taskRecords 'delivery.json') -Raw | ConvertFrom-Json
    if (-not $taskDelivery.complete) { throw 'The import did not finish saving its requested assets.' }
    [IO.File]::WriteAllText($taskState,'Complete: native builds and saved assets. Gameplay testing remains manual.')
} catch {
    [IO.File]::WriteAllText($taskState,('Stopped: '+$_.Exception.Message))
    throw
}
