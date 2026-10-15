param([string]$RecordsRoot='D:\FPS3D\FPSGAME\SourceAssets\HeQueBoss20261014\DungeonE2E\Records',[int]$Seed=92247,[int]$LagMS=0,[int]$LossPercent=0)
$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$auditExe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$auditProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$auditPort=19846
if(Get-NetUDPEndpoint -LocalPort $auditPort -ErrorAction SilentlyContinue){throw "Audit UDP port $auditPort is occupied."}
$auditStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$auditDir=Join-Path $RecordsRoot ('run-'+$auditStamp)
New-Item -ItemType Directory -Force -Path $auditDir | Out-Null
@{seed=$Seed;packet_lag_ms=$LagMS;packet_loss_percent=$LossPercent} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $auditDir 'config.json') -Encoding utf8
$auditProcesses=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-DungeonPeer([string]$role,[string]$map) {
    $peerDir=Join-Path $auditDir $role
    New-Item -ItemType Directory -Force -Path $peerDir | Out-Null
    $arguments=@(('"'+$auditProject+'"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-NoLiveCoding','-NoSteam',
        '-HeQueDungeonAudit',('-HeQueDungeonRole='+$role),('-ColdSteelProfile=HeQueDungeon_'+$auditStamp+'_'+$role),
        ('-UserDir="'+(Join-Path $peerDir 'user')+'"'),('-abslog="'+(Join-Path $peerDir 'engine.log')+'"'),
        ('-HeQueDungeonOutput="'+(Join-Path $peerDir 'result.json')+'"'),('-port='+$auditPort),'-ExecCmds="t.MaxFPS 45"',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    if($LagMS -gt 0){$arguments+=@(('-PktLag='+$LagMS),'-PktLagVariance=20')}
    if($LossPercent -gt 0){$arguments+=('-PktLoss='+$LossPercent)}
    $process=Start-Process -FilePath $auditExe -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $auditProcesses.Add($process);Write-Output "DUNGEON_PEER_STARTED $role PID=$($process.Id) RECORDS=$peerDir";return $process
}
function Wait-DungeonMarker([string]$marker,[System.Diagnostics.Process]$server,[int]$seconds) {
    $deadline=(Get-Date).AddSeconds($seconds)
    while((Get-Date) -lt $deadline) {
        $log=Join-Path $auditDir 'host/engine.log'
        if((Test-Path -LiteralPath $log) -and (Select-String -LiteralPath $log -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker. Logs: $auditDir"}
        foreach($peer in $auditProcesses){if($peer.HasExited){throw "Audit peer PID=$($peer.Id) exited before $marker. Logs: $auditDir"}}
        Start-Sleep -Seconds 2
    }
    throw "Audit timeout waiting for $marker. Logs: $auditDir"
}
try {
    $started=Start-DungeonPeer 'host' ('/Game/GameMaps/L_Dungeon_Randomized?listen?DungeonSeed='+$Seed+'?Name=HeQueAuditHost'+$auditStamp)
    $server=$started[-1];$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-DungeonMarker 'HEQUE_DUNGEON_HOST_READY' $server 600
    $started=Start-DungeonPeer 'guest' ('127.0.0.1:'+$auditPort+'?Name=HeQueAuditGuest'+$auditStamp)
    $started | Where-Object {$_ -is [string]} | Write-Output
    Wait-DungeonMarker 'HEQUE_DUNGEON_RESULT' $server 1200
    $result=Get-Content -LiteralPath (Join-Path $auditDir 'host/result.json') -Raw | ConvertFrom-Json
    Write-Output "DUNGEON_AUDIT_FINISHED PASS=$($result.passed) RECORDS=$auditDir"
    if(-not $result.passed){throw 'HeQue dungeon end-to-end audit failed.'}
} finally {
    foreach($process in $auditProcesses) {
        if(-not $process.HasExited) {
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-HeQueDungeonAudit*' -and $live.CommandLine -like ('*'+$auditStamp+'*')) {Stop-Process -Id $process.Id}
        }
    }
}
