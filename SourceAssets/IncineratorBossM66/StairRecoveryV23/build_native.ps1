param([ValidateSet('FPSGAMEEditor','FPSGAME')][string]$Target='FPSGAMEEditor',[switch]$ForceHeaders,[int]$WaitMinutes=12,[switch]$RunHallAudit)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME';$taskDeadline=(Get-Date).AddMinutes($WaitMinutes)
$taskLock=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
$taskOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Test-M66BuildBusy {
    return @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject'))
    }).Count -gt 0
}
try {
    Write-Output 'Waiting for the current engine/build batch to finish; no processes will be stopped.'
    while(-not $taskHeld){
        try {$taskHeld=$taskLock.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if((Get-Date)-gt $taskDeadline){throw 'Batch stayed busy; source preserved'}
    }
    while(Test-M66BuildBusy){if((Get-Date)-gt $taskDeadline){throw 'Engine/build still busy; source preserved'};Start-Sleep -Seconds 5}
    $taskStem=$Target+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskExtra=@();if($ForceHeaders){$taskExtra+='-ForceHeaderGeneration'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $Target Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 @taskExtra "-Log=$PSScriptRoot/Records/$taskStem.log" *> "$PSScriptRoot/Records/$taskStem-stdout.log"
    $taskCode=$LASTEXITCODE
    [ordered]@{target=$Target;exit_code=$taskCode;log="$PSScriptRoot/Records/$taskStem.log";completed=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/Records/$taskStem.json" -Encoding utf8
    Write-Output "M66_RECOVERY_BUILD target=$Target exit=$taskCode log=$PSScriptRoot/Records/$taskStem.log"
    if($taskCode -eq 0 -and $RunHallAudit){& "$PSScriptRoot/run_network.ps1" -Room Hall -Render}
    exit $taskCode
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskOldSdk
    if($taskHeld){$taskLock.ReleaseMutex()};$taskLock.Dispose()
}
