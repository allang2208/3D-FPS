param()
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject=Split-Path (Split-Path $taskRoot -Parent) -Parent
$taskExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try { $taskHeld=$taskMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    if (-not $taskHeld) { Write-Output 'Waiting for the current UE asset batch.' }
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    }
    $taskEditors=Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -like '*FPSGAME*' }
    if ($taskEditors) { throw 'FPSGAME is already open. Save the ecology revision through the existing editor bridge; do not overwrite loaded maps from another process.' }
    $taskScript=Join-Path $PSScriptRoot $(if ($env:ECOLOGY_SCRIPT) {$env:ECOLOGY_SCRIPT} else {'install_v7_patch.py'})
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog=Join-Path $taskRoot "Receipts/ue-import-$taskStamp.log"
    $taskStdout=Join-Path $taskRoot "Receipts/ue-stdout-$taskStamp.log"
    # This asset-only commandlet uses existing native binaries; do not queue a UBT SDK query.
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & $taskExe (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskLog" *> $taskStdout
    $taskCode=$LASTEXITCODE
    Write-Output "UE_IMPORT_EXIT=$taskCode LOG=$taskLog"
    if ($taskCode -ne 0) { throw "Ecology import stopped. See $taskLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSDK
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
