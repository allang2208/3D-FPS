param([Parameter(Mandatory=$true)][string]$Label)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskOldSeeds=$env:DUNGEON_PROBE_SEEDS
$taskOldLabel=$env:DUNGEON_PROBE_LABEL
$taskOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) }
        catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    }
    # User authorized these two layout-only reproductions on 2026-10-08.
    # probe_layout.py does not assemble geometry or save maps/profiles.
    $env:DUNGEON_PROBE_SEEDS='1668761392,2131734144'
    $env:DUNGEON_PROBE_LABEL=$Label
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskLog=Join-Path $PSScriptRoot "Receipts/$Label.log"
    $taskOutput=Join-Path $PSScriptRoot "Receipts/$Label-stdout.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" '-run=pythonscript' "-script=$taskProject/Tools/Dungeon/probe_layout.py" '-DungeonLayoutProbe' '-nullrhi' '-unattended' '-nop4' '-nosplash' "-abslog=$taskLog" *> $taskOutput
    Write-Output "LAYOUT_REPLAY_EXIT=$LASTEXITCODE REPORT=$taskProject/Saved/DungeonRoutingFix20260927/$Label.json"
} finally {
    $env:DUNGEON_PROBE_SEEDS=$taskOldSeeds
    $env:DUNGEON_PROBE_LABEL=$taskOldLabel
    $env:UE_SKIP_UBT_SDK_SETUP=$taskOldSdk
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
