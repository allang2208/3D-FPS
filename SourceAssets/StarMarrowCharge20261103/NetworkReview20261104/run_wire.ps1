param([switch]$Dedicated)
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$mode=if($Dedicated){'dedicated'}else{'listen'}
$runDir=Join-Path $PSScriptRoot ('Wire/'+$mode+'-'+$stamp)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$port=if($Dedicated){19947}else{19946}
if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Audit port occupied'}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-Peer([string]$role,[string]$map){
    $args=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-Multiprocess','-NoAutoSDK','-NoLiveCoding',
        '-SkillWireAudit','-StarMarrowWireAudit','-PktLag=80','-PktLoss=2',('-ColdSteelProfile=SkillNetworkAudit_StarMarrow_'+$stamp+'_'+$role),('-port='+$port),
        ('-SkillWireOutput="'+(Join-Path $runDir ($role+'.json'))+'"'),('-abslog="'+(Join-Path $runDir ($role+'.log'))+'"'),'-ExecCmds="t.MaxFPS 30"')
    if($role -eq 'host' -and $Dedicated){$args=$args -ne '-game';$args+=@('-server','-StarDedicatedAudit')}
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
    $owned.Add($p);Write-Output "STAR_PEER_STARTED $role PID=$($p.Id)";return $p
}
try {
    while(-not $held) {
        try{$held=$gate.WaitOne(60000)}catch [Threading.AbandonedMutexException]{$held=$true}
        if(-not $held){Write-Output 'Waiting for existing MCP batch'}
    }
    $serverMap='/Engine/Maps/Entry?game=/Script/FPSGAME.SkillWireAuditGameMode';if(-not $Dedicated){$serverMap+='?listen'}
    $output=Start-Peer 'host' $serverMap;$hostProcess=$output[-1]
    $output | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(4);$ready=$false
    while([DateTime]::UtcNow -lt $deadline) {
        if((Test-Path -LiteralPath "$runDir/host.log") -and (Select-String -LiteralPath "$runDir/host.log" -SimpleMatch 'SKILL_WIRE_HOST_READY' -Quiet)){$ready=$true;break}
        if($hostProcess.HasExited){throw 'Audit host exited during startup'}
        Start-Sleep -Seconds 1
    }
    if(-not $ready){throw 'Audit host startup timeout'}
    $output=Start-Peer 'client' ('127.0.0.1:'+$port);$output | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(3)
    while([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath "$runDir/host.json")) {
        if($hostProcess.HasExited){throw 'Audit host exited before result'}
        Start-Sleep -Seconds 1
    }
    if(-not (Test-Path -LiteralPath "$runDir/host.json")){throw 'Audit result timeout'}
    $report=Get-Content -LiteralPath "$runDir/host.json" -Raw | ConvertFrom-Json
    $clientReport=Get-Content -LiteralPath "$runDir/client.json" -Raw | ConvertFrom-Json
    $pass=$report.passed -and $clientReport.passed
    @{directory=$runDir;passed=$pass;transport=('real local UDP '+$mode+' server + client');port=$port;packet_lag_ms=80;packet_loss_percent=2;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/wire-$mode-receipt.json" -Encoding utf8
    Write-Output "STAR_WIRE_FINISHED PASS=$pass PATH=$runDir"
    if(-not $pass){exit 1}
} finally {
    foreach($p in $owned) {
        if(-not $p.HasExited){[void]$p.WaitForExit(5000)}
        if(-not $p.HasExited) {
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-StarMarrowWireAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}
        }
    }
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
