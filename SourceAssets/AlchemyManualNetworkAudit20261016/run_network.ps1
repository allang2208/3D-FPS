param([string]$RecordsRoot='D:\FPS3D\FPSGAME\SourceAssets\AlchemyManualNetworkAudit20261016\Records')
$ErrorActionPreference='Stop'
$auditExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$auditProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$auditPort=19846
if(Get-NetUDPEndpoint -LocalPort $auditPort -ErrorAction SilentlyContinue){throw "Audit UDP port $auditPort is occupied."}
$auditStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$auditDir=Join-Path $RecordsRoot ('sockets-'+$auditStamp)
New-Item -ItemType Directory -Force -Path $auditDir | Out-Null
$auditProcesses=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$auditGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$auditHeld=$false
function Start-AuditPeer([string]$role,[string]$map) {
    $auditLog=Join-Path $auditDir ($role+'.log')
    $auditArgs=@(('"'+$auditProject+'"'),('"'+$map+'"'),'-game','-RenderOffscreen','-windowed','-ResX=640','-ResY=360','-nosound','-unattended','-nosplash',
        '-AlchemyManualNetAudit','-ini:Engine:[ConsoleVariables]:fps.body.AsyncPreload=0,[ConsoleVariables]:fps.body.WorldBodySuppress=1',('-ManualNetRole='+$role),('-ColdSteelProfile=ManualNetAudit_'+$auditStamp+'_'+$role),
        ('-abslog="'+$auditLog+'"'),('-ManualNetOutput="'+(Join-Path $auditDir ($role+'.json'))+'"'),
        ('-port='+$auditPort),('-UserDir='+$auditDir+'/'+$role+'/'),'-ExecCmds="fps.body.AsyncPreload 0,t.MaxFPS 60"')
    $p=Start-Process -FilePath $auditExe -ArgumentList $auditArgs -WindowStyle Hidden -PassThru
    $auditProcesses.Add($p)
    Write-Output "AUDIT_PEER_STARTED $role PID=$($p.Id)"
    return $p
}
function Wait-AuditMarker([string]$marker,[System.Diagnostics.Process]$server,[int]$seconds=300) {
    $deadline=(Get-Date).AddSeconds($seconds)
    while((Get-Date) -lt $deadline) {
        if((Test-Path -LiteralPath (Join-Path $auditDir 'host.log')) -and
            (Select-String -LiteralPath (Join-Path $auditDir 'host.log') -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker. Logs: $auditDir"}
        Start-Sleep -Seconds 1
    }
    throw "Audit timeout waiting for $marker. Logs: $auditDir"
}
try {
    while(!$auditHeld){try{$auditHeld=$auditGate.WaitOne([TimeSpan]::FromSeconds(45))}catch [Threading.AbandonedMutexException]{$auditHeld=$true};if(!$auditHeld){Write-Output 'Waiting for the shared UE batch before the manual network audit.'}}
    $hostOutput=Start-AuditPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.AlchemyManualNetAuditGameMode?listen'
    $auditHost=$hostOutput[-1];$hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'MANUAL_NET_HOST_READY' $auditHost
    $earlyOutput=Start-AuditPeer 'early' ('127.0.0.1:'+$auditPort)
    $earlyOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'MANUAL_NET_LATE_READY' $auditHost
    $auditEarly=$earlyOutput[-1]
    if(-not $auditEarly.WaitForExit(60000)){throw 'Departing audit client did not finish shutdown; preserving the two-peer load limit.'}
    $lateOutput=Start-AuditPeer 'late' ('127.0.0.1:'+$auditPort)
    $lateOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'MANUAL_NET_RESULT' $auditHost
    $result=Get-Content -LiteralPath (Join-Path $auditDir 'host.json') -Raw | ConvertFrom-Json
    Write-Output "AUDIT_FINISHED PASS=$($result.passed) RECORDS=$auditDir"
    if(-not $result.passed){throw 'Manual real socket audit failed.'}
} finally {
    # These are only the hidden command-line peers created by this script.
    foreach($p in $auditProcesses) {
        if(-not $p.HasExited) {
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-AlchemyManualNetAudit*' -and $live.CommandLine -like ('*'+$auditStamp+'*')) {
                Stop-Process -Id $p.Id
            }
        }
    }
    if($auditHeld){$auditGate.ReleaseMutex()}
    $auditGate.Dispose()
}
