param()
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskConfig=Get-Content -LiteralPath (Join-Path $taskRoot 'Config/room.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($taskConfig.production_revision -ge 1) {
    & (Join-Path $taskRoot 'Production20261002/Scripts/install_background.ps1')
    exit 0
}
if ($taskConfig.coffee_polish_revision -ge 7) {
    & (Join-Path $PSScriptRoot 'import_coffee_polish_background_v7.ps1')
    exit 0
}
if ($taskConfig.wall_inset_revision -ge 6) {
    & (Join-Path $PSScriptRoot 'import_wall_inset_background_v6.ps1')
    exit 0
}
if ($taskConfig.room_details_revision -ge 5) {
    & (Join-Path $PSScriptRoot 'import_room_details_background_v5.ps1')
    exit 0
}
if ($taskConfig.scene_polish_revision -ge 4) {
    & (Join-Path $PSScriptRoot 'import_scene_polish_background_v4.ps1')
    exit 0
}
if ($taskConfig.container_open_parts_revision -ge 3) {
    & (Join-Path $PSScriptRoot 'import_container_open_parts_background_v3.ps1')
    exit 0
}
if ($taskConfig.dormitory_layout_revision -ge 2) {
    & (Join-Path $PSScriptRoot 'import_dormitory_variants_background_v2.ps1')
    exit 0
}
if ($taskConfig.container_interaction_revision -ge 1) {
    & (Join-Path $PSScriptRoot 'import_search_containers_background_v1.ps1')
    exit 0
}
$taskProject=Split-Path (Split-Path $taskRoot -Parent) -Parent
$taskUE='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try { $taskHeld=$taskMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    if (-not $taskHeld) { Write-Output 'Waiting for the existing UE asset batch to finish.' }
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    }
    $taskScript=Join-Path $PSScriptRoot 'import_assets.py'
    $taskLog=Join-Path $taskRoot 'Receipts\ue-import.log'
    $taskStdout=Join-Path $taskRoot 'Receipts\ue-import-stdout.log'
    & $taskUE (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nullrhi' "-abslog=$taskLog" *> $taskStdout
    $taskCode=$LASTEXITCODE
    Write-Output "UE_IMPORT_EXIT=$taskCode"
    if ($taskCode -ne 0) { throw "Staff living import failed. See $taskLog" }
} finally {
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
