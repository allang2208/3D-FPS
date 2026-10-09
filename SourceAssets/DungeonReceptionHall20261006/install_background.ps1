param([string]$ScriptName='install.py')
$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskRoot=$PSScriptRoot
$taskExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    Write-Output 'Reception import queued behind existing UE asset writers.'
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
        if (-not $taskHeld) { continue }
        $taskEditors=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -like '*FPSGAME*' }
        if (-not $taskEditors) { break }
        if ($taskEditors | Where-Object { $_.Name -notlike '*-Cmd.exe' }) {
            $taskMutex.ReleaseMutex()
            $taskHeld=$false
            $taskBridgeOutput=Join-Path $taskRoot ('Receipts/live-save-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
            & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript (Join-Path $taskRoot $ScriptName) -QueueWaitSeconds 600 -RequestTimeoutSeconds 600 -OutputFile $taskBridgeOutput -MaxOutputChars 1800
            if ($LASTEXITCODE -ne 0) { throw "Existing-editor save could not finish. See $taskBridgeOutput" }
            return
        }
        # This known producer saves only four alien skeletal-mesh families and
        # their LOD settings. It neither loads nor saves reception assets/maps.
        # Our owned namespace and new map are disjoint; keep the MCP mutex held.
        $taskOverlappingWriters=@($taskEditors | Where-Object { $_.CommandLine -notmatch 'Tools[\\/]MonsterAI[\\/]produce_alien_geometry\.py' })
        if ($taskOverlappingWriters.Count -eq 0) { break }
        $taskMutex.ReleaseMutex()
        $taskHeld=$false
        foreach ($taskWriter in $taskEditors) {
            $taskProcess=Get-Process -Id $taskWriter.ProcessId -ErrorAction SilentlyContinue
            if ($taskProcess) { [void]$taskProcess.WaitForExit(5000) }
        }
    }
    $taskScript=Join-Path $taskRoot $ScriptName
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    New-Item -ItemType Directory -Force -Path (Join-Path $taskRoot 'Receipts') | Out-Null
    $taskLog=Join-Path $taskRoot "Receipts/ue-import-$taskStamp.log"
    $taskStdout=Join-Path $taskRoot "Receipts/ue-stdout-$taskStamp.log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "RECEPTION_IMPORT_STARTED LOG=$taskLog"
    & $taskExe (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskLog" *> $taskStdout
    $taskCode=$LASTEXITCODE
    Write-Output "UE_IMPORT_EXIT=$taskCode LOG=$taskLog"
    if ($taskCode -ne 0) { throw "Reception import stopped. See $taskLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSDK
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
