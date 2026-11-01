$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    for($taskAttempt=0;$taskAttempt -lt 40 -and -not $taskHeld;$taskAttempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    if(-not $taskHeld){throw 'UE batch remains busy; build has not started.'}
    if($env:THUNDER_THROW_GAME_ONLY -ne '1' -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'")){throw 'Preserve running UnrealEditor.exe; normal Editor DLL cannot be replaced.'}
    if($env:THUNDER_THROW_GAME_ONLY -eq '1' -and (Get-CimInstance Win32_Process -Filter "Name='FPSGAME.exe'")){throw 'Preserve running FPSGAME.exe; game binary cannot be replaced.'}
    $taskImports=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
    foreach($taskProcess in $taskImports){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskReceipts=@()
    $taskTargets=if($env:THUNDER_THROW_GAME_ONLY -eq '1') {
        $taskReceipts=@(Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') | ConvertFrom-Json | Where-Object {$_.target -ne 'FPSGAME'})
        @('FPSGAME')
    } else {@('FPSGAMEEditor','FPSGAME')}
    foreach($taskTarget in $taskTargets) {
        $taskLog=Join-Path $PSScriptRoot ('build-'+$taskTarget+'.log')
        & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $taskTarget Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -WaitMutex -NoHotReloadFromIDE *> $taskLog
        $taskExit=$LASTEXITCODE
        $taskReceipts+=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog;finished=(Get-Date).ToString('s')}
        $taskReceipts | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
        Get-Content -LiteralPath $taskLog -Tail 12
        if($taskExit -ne 0){exit $taskExit}
    }
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
