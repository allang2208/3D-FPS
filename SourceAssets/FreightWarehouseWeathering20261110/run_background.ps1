param([string]$ScriptName='install.py')
$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    Write-Output 'Freight warehouse weathering save queued.'
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
        if (-not $taskHeld) { continue }
        $taskAllProcesses=@(Get-CimInstance Win32_Process)
        $taskBuilds=@($taskAllProcesses | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') })
        if ($taskBuilds.Count -gt 0) {
            $taskMutex.ReleaseMutex();$taskHeld=$false
            foreach ($taskBuild in $taskBuilds) { $taskProcess=Get-Process -Id $taskBuild.ProcessId -ErrorAction SilentlyContinue; if($taskProcess){[void]$taskProcess.WaitForExit(5000)} }
            continue
        }
        $taskEditors=@($taskAllProcesses | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -notmatch '(?i)\s-game(?:\s|$)' -and (-not $_.CommandLine -or $_.CommandLine -match '(?i)D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject') })
        if ($taskEditors.Count -eq 0) { break }
        if ($taskEditors | Where-Object { $_.Name -notlike '*-Cmd.exe' }) {
            $taskMutex.ReleaseMutex()
            $taskHeld=$false
            $taskOutput=Join-Path $PSScriptRoot ('Receipts/live-save-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
            & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $PSScriptRoot $ScriptName) -QueueWaitSeconds 600 -RequestTimeoutSeconds 600 -OutputFile $taskOutput -MaxOutputChars 1600
            if ($LASTEXITCODE -ne 0) { throw "Existing editor import stopped: $taskOutput" }
            return
        }
        $taskMutex.ReleaseMutex()
        $taskHeld=$false
        foreach ($taskEditor in $taskEditors) {
            $taskProcess=Get-Process -Id $taskEditor.ProcessId -ErrorAction SilentlyContinue
            if ($taskProcess) { [void]$taskProcess.WaitForExit(5000) }
        }
    }
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog=Join-Path $PSScriptRoot "Receipts/import-$taskStamp.log"
    $taskOutput=Join-Path $PSScriptRoot "Receipts/stdout-$taskStamp.log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "FREIGHT_WEATHERING_STARTED LOG=$taskLog"
    & $taskExe (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$(Join-Path $PSScriptRoot $ScriptName)" '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' "-abslog=$taskLog" *> $taskOutput
    $taskCode=$LASTEXITCODE
    Write-Output "UE_IMPORT_EXIT=$taskCode LOG=$taskLog"
    if ($taskCode -ne 0) { throw "Freight warehouse weathering save stopped: $taskLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSDK
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
