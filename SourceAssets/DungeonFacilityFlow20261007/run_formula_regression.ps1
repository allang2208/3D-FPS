param(
    [Parameter(Mandatory=$true)][string]$Label,
    [Parameter(Mandatory=$true)][string]$SeedFile,
    [switch]$JointLayout,
    [string]$CaseFile,
    [string]$BankFile,
    [switch]$BankOnly,
    [string]$CatalogFile
)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskSeeds=@(Get-Content -Raw -LiteralPath $SeedFile | ConvertFrom-Json)
if ($taskSeeds.Count -eq 0) { throw 'Seed list is empty' }
$taskCaseCount=if($CaseFile){@(Get-Content -Raw -LiteralPath $CaseFile | ConvertFrom-Json).Count}else{$taskSeeds.Count}
$taskSeedText=($taskSeeds | ForEach-Object { [int]$_ }) -join ','
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskOldSeeds=$env:DUNGEON_PROBE_SEEDS
$taskOldLabel=$env:DUNGEON_PROBE_LABEL
$taskOldCases=$env:DUNGEON_PROBE_CASES
$taskOldBank=$env:DUNGEON_PROBE_BANK
$taskOldCatalog=$env:DUNGEON_PROBE_CATALOG
$taskOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
$taskExit=1
try {
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) }
        catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    }
    # User requested inspection/testing on 2026-10-08. Layout only; no assembly,
    # package saves, game world, player profile, or graphical editor startup.
    $env:DUNGEON_PROBE_SEEDS=$taskSeedText
    $env:DUNGEON_PROBE_LABEL=$Label
    $env:DUNGEON_PROBE_CASES=if($CaseFile){(Resolve-Path -LiteralPath $CaseFile).Path}else{$null}
    $env:DUNGEON_PROBE_BANK=if($BankFile){(Resolve-Path -LiteralPath $BankFile).Path}else{$null}
    $env:DUNGEON_PROBE_CATALOG=if($CatalogFile){(Resolve-Path -LiteralPath $CatalogFile).Path}else{$null}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskLog=Join-Path $PSScriptRoot "Receipts/$Label.log"
    $taskOutput=Join-Path $PSScriptRoot "Receipts/$Label-stdout.log"
    $taskExtra=@()
    if($JointLayout -or $BankOnly){$taskExtra+='-DungeonJointLayoutProbe'}
    if($BankOnly){$taskExtra+='-DungeonLayoutBankProbe'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" '-run=pythonscript' "-script=$taskProject/Tools/Dungeon/probe_layout.py" '-DungeonLayoutProbe' '-nullrhi' '-unattended' '-nop4' '-nosplash' "-abslog=$taskLog" @taskExtra *> $taskOutput
    $taskExit=$LASTEXITCODE
    foreach ($taskSuffix in @('.json','-catalog.json')) {
        $taskReport=Join-Path $taskProject "Saved/DungeonRoutingFix20260927/$Label$taskSuffix"
        if (Test-Path -LiteralPath $taskReport) {
            Copy-Item -LiteralPath $taskReport -Destination (Join-Path $PSScriptRoot "Receipts/$Label$taskSuffix")
        }
    }
    Write-Output "LAYOUT_REGRESSION_EXIT=$taskExit LABEL=$Label CASES=$taskCaseCount"
} finally {
    $env:DUNGEON_PROBE_SEEDS=$taskOldSeeds
    $env:DUNGEON_PROBE_LABEL=$taskOldLabel
    $env:DUNGEON_PROBE_CASES=$taskOldCases
    $env:DUNGEON_PROBE_BANK=$taskOldBank
    $env:DUNGEON_PROBE_CATALOG=$taskOldCatalog
    $env:UE_SKIP_UBT_SDK_SETUP=$taskOldSdk
    if ($taskHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
exit $taskExit
