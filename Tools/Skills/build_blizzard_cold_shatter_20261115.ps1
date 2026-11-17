$ErrorActionPreference='Stop'
$blizzardRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$blizzardOut=Join-Path $blizzardRoot 'SourceAssets/BlizzardColdShatter20261115'
$blizzardSaved=Get-Content -LiteralPath (Join-Path $blizzardOut 'assets-saved.json') -Raw | ConvertFrom-Json
$blizzardGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$blizzardHeld=$false
try {
    while (-not $blizzardHeld) {
        $blizzardHeld=$blizzardGate.WaitOne([TimeSpan]::FromSeconds(45))
        if (-not $blizzardHeld) {Write-Output 'Waiting for shared UE build window.'}
    }
    $blizzardEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$null -eq $_.ThreadCount -or $_.ThreadCount -gt 0})
    if ($blizzardEditors.Count) {throw 'An editor is active; preserve it. Native build remains pending.'}
    $blizzardLog=Join-Path $blizzardOut 'native-build.log'
    $blizzardConsole=Join-Path $blizzardOut 'native-build-console.log'
    $blizzardArgs=@('-Target=FPSGAMEEditor Win64 Development','-Target=FPSGAME Win64 Development',
        ('-Project='+(Join-Path $blizzardRoot 'FPSGAME.uproject')),'-WaitMutex','-NoHotReload','-NoHotReloadFromIDE',
        '-NoUBA','-MaxParallelActions=4',('-Log='+$blizzardLog))
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' @blizzardArgs *> $blizzardConsole
    $blizzardExit=$LASTEXITCODE
    @{exit_code=$blizzardExit;saved_assets=@($blizzardSaved.saved_assets);native_log=$blizzardLog;
      runtime_change='Blizzard room-aware cold mist and pooled original IceSpike shatter with spinning ISM chips';
      shatter_components_per_zone=3;fragment_slots_per_zone=24;
      game_started=$false;editor_ui_started=$false;rendered=$false;tested=$false} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $blizzardOut 'delivery.json') -Encoding UTF8
    if ($blizzardExit -ne 0) {throw ('Blizzard cold/shatter build failed: '+$blizzardLog)}
    Write-Output 'BLIZZARD_COLD_SHATTER_BUILT_EDITOR_AND_GAME'
} finally {
    if ($blizzardHeld) {$blizzardGate.ReleaseMutex()}
    $blizzardGate.Dispose()
}
