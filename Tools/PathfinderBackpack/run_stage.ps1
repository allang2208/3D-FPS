param([Parameter(Mandatory=$true)][string]$Stage,[switch]$NullRHI,[switch]$NewRevisionOnly)
$ErrorActionPreference='Stop'
$packProject='D:/FPS3D/FPSGAME'
$packRoot=Join-Path $packProject 'SourceAssets/PathfinderBackpack20261023/OrientationFitR2_20261024'
$packScript=Join-Path $packProject ('Tools/PathfinderBackpack/'+$Stage+'.py')
$packGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$packHeld=$false
try {
    try {$packHeld=$packGate.WaitOne()} catch [Threading.AbandonedMutexException] {$packHeld=$true}
    $packBusy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and -not $NewRevisionOnly) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($packBusy.Count) {throw 'An editor or build is active. Preserve it; resume this scoped asset stage when available.'}
    if($NewRevisionOnly) {
        if($Stage -notin @('save_materials_r2','save_display_r2','save_worn_r2','save_harness_r2','save_jason_r2')) {throw 'NewRevisionOnly is restricted to the isolated backpack revision.'}
        $env:PATHFINDER_NEW_ASSETS_ONLY='1'
    }
    $packLog=Join-Path $packRoot ($Stage+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output ('PATHFINDER_LOG '+$packLog)
    $packArgs=@((Join-Path $packProject 'FPSGAME.uproject'),'-run=pythonscript',('-script='+$packScript),'-unattended','-nop4','-nosplash','-nosound',('-abslog='+$packLog))
    if($NullRHI) {$packArgs+='-nullrhi'} else {$packArgs+=@('-RenderOffscreen','-AllowCommandletRendering','-d3d12')}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @packArgs *> ($packLog+'.stdout.txt')
    $packCode=$LASTEXITCODE
    Get-Content -LiteralPath ($packLog+'.stdout.txt') -Tail 8
    exit $packCode
} finally {
    if($packHeld) {$packGate.ReleaseMutex()}
    $packGate.Dispose()
}
