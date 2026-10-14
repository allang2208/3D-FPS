$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskProject = Split-Path (Split-Path $taskRoot -Parent) -Parent
$taskExe = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskMutex = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
$taskPreviousSDK = $env:UE_SKIP_UBT_SDK_SETUP
try {
    try { $taskHeld = $taskMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    if (-not $taskHeld) { Write-Output 'Waiting for the current UE asset batch.' }
    while (-not $taskHeld) {
        try { $taskHeld = $taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    }
    # This script only creates this absent target. It never saves production
    # maps, shared meshes/materials, or other loaded packages (no SaveAll).
    # Existing editor/PIE sessions can keep using those read-only inputs.
    $taskTarget = Join-Path $taskProject 'Content/GameMaps/Design/L_StaffLiving_Theme_Subject.umap'
    if (Test-Path -LiteralPath $taskTarget) { throw 'Preserve existing staff test map. Updates must use its owning editor or a closed-editor window.' }
    New-Item -ItemType Directory -Path (Join-Path $taskRoot 'Receipts') -Force | Out-Null
    $taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog = Join-Path $taskRoot "Receipts/ue-create-$taskStamp.log"
    $taskStdout = Join-Path $taskRoot "Receipts/ue-stdout-$taskStamp.log"
    $taskScript = Join-Path $PSScriptRoot 'create_subject.py'
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & $taskExe (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskLog" *> $taskStdout
    $taskCode = $LASTEXITCODE
    Write-Output "STAFF_TEST_CREATE_EXIT=$taskCode LOG=$taskLog"
    if ($taskCode -ne 0) { throw "Staff-living map creation stopped. See $taskLog" }
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $taskPreviousSDK
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
