$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskRecord=Join-Path $PSScriptRoot 'build_receipt.json'
$taskStatus=[ordered]@{complete=$false;targets=@();runtime_tested=$false;editor_started=$false}
function Write-TaskRecord {
    $taskStatus | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskRecord -Encoding UTF8
}
Write-TaskRecord
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'}).Count -gt 0) {
        Start-Sleep -Seconds 5
    }
    for ($taskAttempt=0; $taskAttempt -lt 20 -and -not $taskHeld; $taskAttempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    if (-not $taskHeld) {throw 'Asset/build gate remains busy; no build started.'}
    foreach ($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
        while (@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject')}).Count -gt 0) {
            Start-Sleep -Seconds 5
        }
        if (@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'}).Count -gt 0) {
            throw 'Editor reopened; no regular build started.'
        }
        $taskLog=Join-Path $PSScriptRoot ($taskTarget+'-build.log')
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        Write-Output ('BUILDING '+$taskTarget)
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development ('-Project='+$taskRoot+'/FPSGAME.uproject') -NoHotReloadFromIDE -NoLiveCoding -MaxParallelActions=4 *> $taskLog
        $taskExit=$LASTEXITCODE
        $taskStatus.targets+=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog}
        Write-TaskRecord
        if ($taskExit -ne 0) {throw "Regular build failed: $taskTarget ($taskExit)"}
        Write-Output ('BUILT '+$taskTarget)
    }
    $taskStatus.complete=$true
    Write-TaskRecord
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
