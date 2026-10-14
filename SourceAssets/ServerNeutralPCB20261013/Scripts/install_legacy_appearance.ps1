$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch mutex unavailable; authored models preserved'}
    if (Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'UnrealEditor.exe' -or $_.Name -eq 'UnrealEditor-Cmd.exe') -and $_.CommandLine -like '*FPSGAME.uproject*' }) { throw 'Preserve loaded main-project assets; legacy texture update deferred' }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $taskRoot 'UEImportHost/ServerNeutralPCBImport.uproject') '-run=pythonscript' "-script=$PSScriptRoot\apply_legacy_appearance.py" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskRoot\Receipts\ue-legacy-appearance.log" *> (Join-Path $taskRoot 'Receipts/legacy-appearance-stdout.log')
    $taskExit=$LASTEXITCODE
    Write-Output "SERVER_REFERENCE_STAGED_IMPORT_EXIT=$taskExit"
    Select-String -LiteralPath (Join-Path $taskRoot 'Receipts/legacy-appearance-stdout.log') -Pattern 'SEARCH_SERVER_REFERENCE|Error:|Traceback' | Select-Object -Last 12
    exit $taskExit
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
