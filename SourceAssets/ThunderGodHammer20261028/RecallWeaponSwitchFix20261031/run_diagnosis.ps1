$ErrorActionPreference='Stop'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    for($taskAttempt=0;$taskAttempt -lt 20 -and -not $taskHeld;$taskAttempt++){
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    }
    if(-not $taskHeld){throw 'UE batch busy; diagnosis not started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Preserve running editor; diagnosis not started.'}
    if(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool.dll'}).Count){throw 'Build still running; diagnosis not started.'}
    $taskLog=Join-Path $PSScriptRoot ('diagnosis-'+$taskStamp+'.log')
    $taskReport=Join-Path $PSScriptRoot ('diagnosis-'+$taskStamp+'.json')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=ThunderHammerRecallAudit -WeaponSwitchOnly "-Out=$taskReport" -unattended -nop4 -nosplash -NoSound -NoLiveCoding -NullRHI  "-abslog=$taskLog" *> (Join-Path $PSScriptRoot ('diagnosis-'+$taskStamp+'-console.log'))
    $taskCode=$LASTEXITCODE
    if(Test-Path -LiteralPath $taskReport){Get-Content -LiteralPath $taskReport}
    else {Get-Content -LiteralPath $taskLog -Tail 20}
    exit $taskCode
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
