param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset/build batch remains busy; no build started.'}
    $taskWaiting=$false
    while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool.dll'}).Count -gt 0){
        if(-not $taskWaiting){Write-Output 'Waiting for the existing Unreal build to finish.';$taskWaiting=$true}
        Start-Sleep -Seconds 5
    }
    foreach($taskTarget in $Targets) {
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -match '^UnrealEditor' -and ((-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or $_.Name -match '^FPSGAME.*\.exe$'})
        if($taskBusy.Count -gt 0){throw 'Preserve the running editor/game; no binary replacement started.'}
        $taskLog=Join-Path $PSScriptRoot ($taskTarget+'-'+$taskStamp+'.log')
        $taskConsole=Join-Path $PSScriptRoot ($taskTarget+'-'+$taskStamp+'-console.log')
        Write-Output ('Building '+$taskTarget)
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReloadFromIDE -NoLiveCoding "-Log=$taskLog" *> $taskConsole
        $taskCode=$LASTEXITCODE
        [ordered]@{target=$taskTarget;exit_code=$taskCode;log=$taskLog;finished=(Get-Date).ToString('o');runtime_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot ($taskTarget+'-'+$taskStamp+'-receipt.json')) -Encoding utf8
        Get-Content -LiteralPath $taskConsole -Tail 12
        if($taskCode -ne 0){exit $taskCode}
    }
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
