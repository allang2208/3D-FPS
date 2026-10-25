param([Parameter(Mandatory=$true)][string]$Stage,[switch]$NullRHI,[switch]$NewRevisionOnly,[string]$Revision='ContactAuditR1')
$ErrorActionPreference='Stop'
$packProject='D:/FPS3D/FPSGAME'
if($Revision -notmatch '^[A-Za-z0-9_-]+$'){throw 'Invalid scoped revision name'}
$packRoot=Join-Path $packProject ('SourceAssets/BackpackFit20261024/'+$Revision)
$env:BACKPACK_FIT_RUN_DIR=$packRoot
$packScript=Join-Path $packProject ('Tools/BackpackFit/'+$Stage+'.py')
$packGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$packHeld=$false
try {
    # Wait for active native builds before taking the asset batch mutex.
    while($true) {
        $packBuild=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $packBuild.Count){break}
        try {Wait-Process -Id $packBuild[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $packBuild[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    try {$packHeld=$packGate.WaitOne()} catch [Threading.AbandonedMutexException] {$packHeld=$true}
    $packBusy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
        # The icon producer only reads saved UE assets and writes this item's PNG.
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and -not $NewRevisionOnly -and $Stage -notin @('capture','contact','capacity')) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($packBusy.Count) {throw 'An editor or build is active. Preserve it; resume this scoped asset stage when available.'}
    if($NewRevisionOnly) {
        if($Stage -ne 'save_assets') {throw 'NewRevisionOnly is restricted to the isolated backpack fit asset producer.'}
        $env:BACKPACK_FIT_NEW_ASSETS_ONLY='1'
    }
    $packLog=Join-Path $packRoot ($Stage+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output ('BACKPACK_FIT_LOG '+$packLog)
    $packArgs=@((Join-Path $packProject 'FPSGAME.uproject'),'-unattended','-nop4','-nosplash','-nosound',('-abslog='+$packLog))
    if($Stage -eq 'contact') {
        $packArgs+=@('-run=BackpackCapacityAudit','-ContactOnly','-GravityCheck',('-ReportDir='+$packRoot))
    } elseif($Stage -eq 'capacity') {
        $packArgs+=@('-run=BackpackCapacityAudit','-SyntheticOnly',('-ReportDir='+$packRoot))
    } else {$packArgs+=@('-run=pythonscript',('-script='+$packScript))}
    if($NullRHI) {$packArgs+='-nullrhi'} else {$packArgs+=@('-RenderOffscreen','-AllowCommandletRendering','-d3d12')}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @packArgs *> ($packLog+'.stdout.txt')
    $packCode=$LASTEXITCODE
    Get-Content -LiteralPath ($packLog+'.stdout.txt') -Tail 8
    exit $packCode
} finally {
    if($packHeld) {$packGate.ReleaseMutex()}
    $packGate.Dispose()
}
