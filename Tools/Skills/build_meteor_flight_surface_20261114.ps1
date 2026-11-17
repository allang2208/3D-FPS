$ErrorActionPreference='Stop'
$meteorRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$meteorOut=Join-Path $meteorRoot 'SourceAssets/MeteorFlightSurface20261114'
$meteorSaved=Get-Content -LiteralPath (Join-Path $meteorOut 'assets-saved.json') -Raw | ConvertFrom-Json
$meteorGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$meteorHeld=$false
try {
    while (-not $meteorHeld) {
        $meteorHeld=$meteorGate.WaitOne([TimeSpan]::FromSeconds(45))
        if (-not $meteorHeld) {Write-Output 'Waiting for shared UE build window.'}
    }
    $meteorEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$null -eq $_.ThreadCount -or $_.ThreadCount -gt 0})
    if ($meteorEditors.Count) {throw 'An editor is active; preserve it and the saved assets. Native build remains pending.'}
    # No executing editor remains. Let the ordinary linker handle output files;
    # a zero-thread Windows snapshot can fail an exclusive probe even when the
    # standard build can replace its output. Never force-close that process.
    $meteorLog=Join-Path $meteorOut 'native-build.log'
    $meteorConsole=Join-Path $meteorOut 'native-build-console.log'
    $meteorArgs=@('-Target=FPSGAMEEditor Win64 Development','-Target=FPSGAME Win64 Development',
        ('-Project='+(Join-Path $meteorRoot 'FPSGAME.uproject')),'-WaitMutex','-NoHotReload','-NoHotReloadFromIDE',
        '-NoUBA','-MaxParallelActions=4',('-Log='+$meteorLog))
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' @meteorArgs *> $meteorConsole
    $meteorExit=$LASTEXITCODE
    @{exit_code=$meteorExit;saved_assets=@($meteorSaved.saved_assets);native_log=$meteorLog;
      runtime_change='Send actual rock rotation axes to surface-attached flame roots';
      game_started=$false;editor_ui_started=$false;rendered=$false;tested=$false} |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $meteorOut 'delivery.json') -Encoding UTF8
    if ($meteorExit -ne 0) {throw ('Meteor flight build failed: '+$meteorLog)}
    Write-Output 'METEOR_FLIGHT_SURFACE_BUILT_EDITOR_AND_GAME'
} finally {
    if ($meteorHeld) {$meteorGate.ReleaseMutex()}
    $meteorGate.Dispose()
}
