$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch mutex unavailable; authored models preserved'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $taskRoot 'UEImportHost/SearchMaintenanceImport.uproject') '-run=pythonscript' "-script=$PSScriptRoot\import_assets.py" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskRoot\Receipts\ue-staged-import.log" *> (Join-Path $taskRoot 'Receipts/staged-import-stdout.log')
    $taskExit=$LASTEXITCODE
    Write-Output "MAINTENANCE_STAGED_IMPORT_EXIT=$taskExit"
    Select-String -LiteralPath (Join-Path $taskRoot 'Receipts/staged-import-stdout.log') -Pattern 'SEARCH_MAINTENANCE|Error:|Traceback' | Select-Object -Last 12
    exit $taskExit
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
