param([string]$ScriptName='install.py', [switch]$RenderShaders)
$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    Write-Output 'Hall lighting save queued.'
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
        if (-not $taskHeld) { continue }
        $taskEditors=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -like '*FPSGAME*' })
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
    Write-Output "HALL_LIGHTING_SAVE_STARTED LOG=$taskLog"
    $taskRenderArgs=if ($RenderShaders) { @('-AllowCommandletRendering','-RenderOffscreen') } else { @('-nullrhi') }
    & $taskExe (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$(Join-Path $PSScriptRoot $ScriptName)" '-unattended' '-nop4' '-nosplash' @taskRenderArgs "-abslog=$taskLog" *> $taskOutput
    $taskCode=$LASTEXITCODE
    Write-Output "UE_IMPORT_EXIT=$taskCode LOG=$taskLog"
    if ($taskCode -ne 0) { throw "Hall lighting save stopped: $taskLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSDK
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
