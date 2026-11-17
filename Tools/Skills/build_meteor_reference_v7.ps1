param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$meteorRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$meteorOut = Join-Path $meteorRoot 'SourceAssets/MeteorImpactReferenceV7_20261114'
$meteorReceipt = Join-Path $meteorOut 'asset-receipt.json'
if (-not (Test-Path -LiteralPath $meteorReceipt)) { throw 'Save V7 assets before integration.' }
$meteorSaved = Get-Content -Raw -Encoding UTF8 -LiteralPath $meteorReceipt | ConvertFrom-Json
if (-not $meteorSaved.complete) { throw 'V7 asset save did not complete.' }
function Get-MeteorBuildBusy {
    $processes = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($processes.Count -gt 0) { return $true }
    foreach ($relative in @('Binaries/Win64/UnrealEditor-FPSGAME.dll','Binaries/Win64/FPSGAME.exe')) {
        $binary = Join-Path $meteorRoot $relative
        if (Test-Path -LiteralPath $binary) {
            try {
                $stream = [IO.File]::Open($binary,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
                $stream.Dispose()
            } catch { return $true }
        }
    }
    return $false
}
$meteorAnnounced = $false
while (Get-MeteorBuildBusy) {
    if (-not $meteorAnnounced) { Write-Output 'Waiting for the active native build or loaded output binary; no process will be stopped.'; $meteorAnnounced = $true }
    Start-Sleep -Seconds 5
}
& 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' (Join-Path $meteorRoot 'Tools/Skills/install_meteor_reference_v7.py')
if ($LASTEXITCODE -ne 0) { throw 'Source integration stopped; preserve current files.' }
$meteorStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$meteorLog = Join-Path $meteorOut ('native-build-' + $meteorStamp + '.log')
$meteorConsole = Join-Path $meteorOut ('native-build-console-' + $meteorStamp + '.log')
$meteorStart = [DateTimeOffset]::Now.ToString('o')
$meteorArgs = @('-Target=FPSGAMEEditor Win64 Development','-Target=FPSGAME Win64 Development',
    ('-Project=' + (Join-Path $meteorRoot 'FPSGAME.uproject')),'-NoHotReload','-NoHotReloadFromIDE',
    '-NoUBA','-MaxParallelActions=4',('-Log=' + $meteorLog))
& (Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat') @meteorArgs *> $meteorConsole
$meteorExit = $LASTEXITCODE
$meteorDelivery = @{
    status = $(if ($meteorExit -eq 0) { 'impact_assets_saved_integrated_game_and_editor_built' } else { 'impact_assets_saved_integrated_build_failed' })
    started_at = $meteorStart
    finished_at = [DateTimeOffset]::Now.ToString('o')
    exit_code = $meteorExit
    native_log = $meteorLog
    saved_assets = @($meteorSaved.saved_assets)
    max_particles = 61
    smoke_budget = 16
    interactive_editor_opened = $false
    game_started = $false
    runtime_tested = $false
    visual_match_claimed = $false
    source = 'Original pressure impulse rebuilt from observed reference timing and layers'
    preserved = @('rock and fragments','V6 flight','V4 low ground fire','gameplay values','sound','camera','scorch')
}
$meteorDelivery | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $meteorOut 'delivery.json') -Encoding UTF8
if ($meteorExit -ne 0) { throw ('Meteor native build failed; see ' + $meteorLog) }
Write-Output ('METEOR_V7_DELIVERED ' + $meteorLog)
