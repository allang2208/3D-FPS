$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/AlchemyManualNetworkAudit20261016'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$previousSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while (!$held) {
        try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(45))}
        catch [Threading.AbandonedMutexException] {$held=$true}
        if (!$held) {Write-Output 'Waiting for the shared UE batch.'}
    }
    $active=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe') -and $_.CommandLine -match 'FPSGAME') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($active.Count) {Write-Output 'Existing project process/build is active; preserving it.'; exit 75}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $attemptRoot=Join-Path $taskRoot ('Audit-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    $userRoot=Join-Path $taskRoot 'IsolatedUser'
    New-Item -ItemType Directory -Force -Path $attemptRoot,$userRoot | Out-Null
    Write-Output "Running the offscreen manual flow audit; report $attemptRoot/report.txt"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=AlchemyManualFlowAudit' '-AllowCommandletRendering' '-RenderOffscreen' `
        '-unattended' '-nop4' '-nosplash' '-nosound' "-UserDir=$userRoot/" `
        "-Output=$attemptRoot/report.txt" "-abslog=$attemptRoot/engine.log" *> "$attemptRoot/console.log"
    $auditExit=$LASTEXITCODE
    $nativeExit=$auditExit
    # Shader fallback is logged as Warning, even when all interaction assertions pass.
    $materialFailures=@(Get-Content -LiteralPath "$attemptRoot/engine.log" | Where-Object {
        $_ -match 'ManualV[0-9]+[/\\]' -and $_ -match 'Failed to compile Material|Default Material will be used'
    })
    if ($auditExit -eq 0 -and $materialFailures.Count -gt 0) {$auditExit=1}
    @{exit_code=$auditExit;native_exit_code=$nativeExit;material_failures=$materialFailures;report="$attemptRoot/report.txt";visible_editor=$false;gameplay_map=$false} |
        ConvertTo-Json | Set-Content -Encoding UTF8 "$attemptRoot/result.json"
    Write-Output "Manual flow audit exit code: $auditExit; result $attemptRoot/result.json"
    exit $auditExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$previousSdk
    if ($held) {$gate.ReleaseMutex()}
    $gate.Dispose()
}
