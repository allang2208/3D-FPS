param([string]$ScriptName='install.py')
$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskRoot=$PSScriptRoot
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
    $taskEditors=Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -like '*FPSGAME*' }
    if ($taskEditors) { throw 'FPSGAME already has an editor or commandlet. Use the existing editor bridge or wait for the active writer.' }
    $taskScript=Join-Path $taskRoot $ScriptName
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    New-Item -ItemType Directory -Force -Path (Join-Path $taskRoot 'Receipts') | Out-Null
    $taskLog=Join-Path $taskRoot "Receipts/ue-import-$taskStamp.log"
    $taskStdout=Join-Path $taskRoot "Receipts/ue-stdout-$taskStamp.log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & $taskExe (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskLog" *> $taskStdout
    $taskCode=$LASTEXITCODE
    Write-Output "UE_IMPORT_EXIT=$taskCode LOG=$taskLog"
    if ($taskCode -ne 0) { throw "Power upper-room import stopped. See $taskLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSDK
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
