param([ValidateSet('assets','native')][string]$Stage='assets')
$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$reviewHeld=$false
try {
    # One queued request; bounded waits keep the supervising chat responsive.
    for($reviewAttempt=0;$reviewAttempt -lt 10 -and -not $reviewHeld;$reviewAttempt++){
        try {$reviewHeld=$reviewGate.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$reviewHeld=$true}
    }
    if(-not $reviewHeld){throw 'UE batch busy; no review process launched.'}
    $reviewProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
    $reviewDLL=Join-Path (Split-Path -Parent $reviewProject) 'Binaries\Win64\UnrealEditor-FPSGAME.dll'
    $reviewArgs=@($reviewProject,'-unattended','-nop4','-nosplash','-nosound','-nullrhi','-NoLiveCoding',('-abslog='+$PSScriptRoot+'\'+$Stage+'-engine.log'))
    if($Stage -eq 'assets'){$reviewArgs+=@('-run=pythonscript',('-script='+$PSScriptRoot+'\audit_assets.py'))}
    else{$reviewArgs+=@('-run=WarhammerModificationAudit','-Definition=ue_thunder_god_hammer',('-Out='+$PSScriptRoot+'\native-result.json'))}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' @reviewArgs *> (Join-Path $PSScriptRoot ($Stage+'-console.log'))
    $reviewExit=$LASTEXITCODE
    @{stage=$Stage;project=$reviewProject;exit_code=$reviewExit;finished=(Get-Date).ToString('o');dll_sha256=(Get-FileHash -LiteralPath $reviewDLL).Hash} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot ($Stage+'-execution.json')) -Encoding utf8
    Write-Output "THUNDER_REVIEW $Stage exit=$reviewExit"
    exit $reviewExit
}finally{if($reviewHeld){$reviewGate.ReleaseMutex()};$reviewGate.Dispose()}
