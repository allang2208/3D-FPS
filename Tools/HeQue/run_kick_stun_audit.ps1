param([string]$RecordsRoot='D:\FPS3D\FPSGAME\SourceAssets\HeQueBoss20261014\KickCollisionStunV01\Validation\Records',[switch]$Edges,[switch]$EdgesOnly,[int]$LagMS=0,[int]$LossPercent=0)
$ErrorActionPreference='Stop'
$kickExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$kickProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$kickPort=19842
if(Get-NetUDPEndpoint -LocalPort $kickPort -ErrorAction SilentlyContinue){throw "Audit UDP port $kickPort is occupied."}
$kickStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$kickDir=Join-Path $RecordsRoot ('sockets-'+$kickStamp)
New-Item -ItemType Directory -Force -Path $kickDir | Out-Null
@{edges=[bool]$Edges;edges_only=[bool]$EdgesOnly;packet_lag_ms=$LagMS;packet_lag_variance_ms=$(if($LagMS -gt 0){20}else{0});packet_loss_percent=$LossPercent} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $kickDir 'run-config.json') -Encoding utf8
$kickProcesses=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-KickPeer([string]$role,[string]$map) {
    $kickArguments=@(('"'+$kickProject+'"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-HeQueKickStunAudit',('-HeQueKickAuditRole='+$role),('-ColdSteelProfile=HeQueKickAudit_'+$kickStamp+'_'+$role),
        ('-abslog="'+(Join-Path $kickDir ($role+'.log'))+'"'),
        ('-HeQueKickAuditOutput="'+(Join-Path $kickDir ($role+'.json'))+'"'),('-port='+$kickPort),'-ExecCmds="t.MaxFPS 60"')
    if($Edges){$kickArguments+='-HeQueKickEdges'}
    if($EdgesOnly){$kickArguments+='-HeQueKickEdgesOnly'}
    if($LagMS -gt 0){$kickArguments+=@(('-PktLag='+$LagMS),'-PktLagVariance=20')}
    if($LossPercent -gt 0){$kickArguments+=('-PktLoss='+$LossPercent)}
    $process=Start-Process -FilePath $kickExe -ArgumentList $kickArguments -WindowStyle Hidden -PassThru
    $kickProcesses.Add($process);Write-Output "KICK_PEER_STARTED $role PID=$($process.Id)";return $process
}
function Wait-KickMarker([string]$marker,[System.Diagnostics.Process]$server) {
    $deadline=(Get-Date).AddSeconds(180)
    while((Get-Date) -lt $deadline) {
        $log=Join-Path $kickDir 'host.log'
        if((Test-Path -LiteralPath $log) -and (Select-String -LiteralPath $log -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker. Logs: $kickDir"}
        Start-Sleep -Seconds 1
    }
    throw "Audit timeout waiting for $marker. Logs: $kickDir"
}
try {
    $hostOutput=Start-KickPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.HeQueKickStunGameMode?listen'
    $kickHost=$hostOutput[-1];$hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-KickMarker 'HEQUE_KICK_HOST_READY' $kickHost
    $guestOutput=Start-KickPeer 'guest' ('127.0.0.1:'+$kickPort)
    $guestOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-KickMarker 'HEQUE_KICK_RESULT' $kickHost
    $result=Get-Content -LiteralPath (Join-Path $kickDir 'host.json') -Raw | ConvertFrom-Json
    Write-Output "KICK_AUDIT_FINISHED PASS=$($result.passed) RECORDS=$kickDir"
    if(-not $result.passed){throw 'HeQue kick/stun audit failed.'}
} finally {
    foreach($process in $kickProcesses) {
        if(-not $process.HasExited) {
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-HeQueKickStunAudit*' -and $live.CommandLine -like ('*'+$kickStamp+'*')) {
                Stop-Process -Id $process.Id
            }
        }
    }
}
