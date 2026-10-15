param([string]$RecordsRoot='D:\FPS3D\FPSGAME\SourceAssets\HeQueBoss20261014\NetworkAuditV01\Records')
$ErrorActionPreference='Stop'
$auditExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$auditProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$auditPort=19841
if(Get-NetUDPEndpoint -LocalPort $auditPort -ErrorAction SilentlyContinue){throw "Audit UDP port $auditPort is occupied."}
$auditStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$auditDir=Join-Path $RecordsRoot ('sockets-'+$auditStamp)
New-Item -ItemType Directory -Force -Path $auditDir | Out-Null
$auditProcesses=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-AuditPeer([string]$role,[string]$map) {
    $auditLog=Join-Path $auditDir ($role+'.log')
    $auditArgs=@(('"'+$auditProject+'"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-HeQueNetAudit',('-HeQueAuditLabel='+$role),('-ColdSteelProfile=HeQueAudit_'+$auditStamp+'_'+$role),
        ('-abslog="'+$auditLog+'"'),('-HeQueAuditOutput="'+(Join-Path $auditDir ($role+'.json'))+'"'),
        ('-port='+$auditPort),'-ExecCmds="t.MaxFPS 60"')
    $p=Start-Process -FilePath $auditExe -ArgumentList $auditArgs -WindowStyle Hidden -PassThru
    $auditProcesses.Add($p)
    Write-Output "AUDIT_PEER_STARTED $role PID=$($p.Id)"
    return $p
}
function Wait-AuditMarker([string]$marker,[System.Diagnostics.Process]$server,[int]$seconds=180) {
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
    $hostOutput=Start-AuditPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.HeQueNetAuditGameMode?listen'
    $auditHost=$hostOutput[-1];$hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'HEQUE_NET_HOST_READY' $auditHost
    $earlyOutput=Start-AuditPeer 'early' ('127.0.0.1:'+$auditPort)
    $earlyOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'HEQUE_NET_LATE_READY' $auditHost
    $lateOutput=Start-AuditPeer 'late' ('127.0.0.1:'+$auditPort)
    $lateOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'HEQUE_NET_RESULT' $auditHost
    $result=Get-Content -LiteralPath (Join-Path $auditDir 'host.json') -Raw | ConvertFrom-Json
    Write-Output "AUDIT_FINISHED PASS=$($result.passed) RECORDS=$auditDir"
    if(-not $result.passed){throw 'HeQue real socket audit failed.'}
} finally {
    # These are only the hidden command-line peers created by this script.
    foreach($p in $auditProcesses) {
        if(-not $p.HasExited) {
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-HeQueNetAudit*' -and $live.CommandLine -like ('*'+$auditStamp+'*')) {
                Stop-Process -Id $p.Id
            }
        }
    }
}
