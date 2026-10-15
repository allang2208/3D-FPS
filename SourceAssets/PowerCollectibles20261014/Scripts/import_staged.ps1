$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPreviousSdkSkip=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch mutex unavailable; authored models preserved'}
    # Content-only authoring uses the existing SDK state and does not need a UBT platform validation build.
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $taskRoot 'UEImportHost/PowerCollectiblesImport.uproject') '-run=pythonscript' "-script=$PSScriptRoot\import_assets.py" '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' "-abslog=$taskRoot\Receipts\ue-staged-import.log" *> (Join-Path $taskRoot 'Receipts/staged-import-stdout.log')
    $taskExit=$LASTEXITCODE
    Write-Output "POWER_TOOLS_STAGED_IMPORT_EXIT=$taskExit"
    Select-String -LiteralPath (Join-Path $taskRoot 'Receipts/staged-import-stdout.log') -Pattern 'POWER_TOOL|Error:|Traceback' | Select-Object -Last 12
    exit $taskExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSdkSkip
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
