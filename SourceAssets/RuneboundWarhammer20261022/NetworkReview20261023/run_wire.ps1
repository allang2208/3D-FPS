$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$runDir=Join-Path $PSScriptRoot ('Wire/'+$stamp)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$port=19923
if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Audit port occupied'}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-Peer([string]$role,[string]$map){
    $args=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-Multiprocess','-NoAutoSDK','-NoLiveCoding',
        '-RuneboundReviewWire','-PktLag=80','-PktLoss=2',('-ColdSteelProfile=SkillNetworkAudit_Runebound_'+$stamp+'_'+$role),('-port='+$port),
        ('-RuneboundReviewOutput="'+(Join-Path $runDir ($role+'.json'))+'"'),('-abslog="'+(Join-Path $runDir ($role+'.log'))+'"'),'-ExecCmds="fps.body.WorldBodySuppress 1,t.MaxFPS 30"')
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
    $owned.Add($p);Write-Output "RUNEBOUND_PEER_STARTED $role PID=$($p.Id)";return $p
}
try {
    while(-not $held){try{$held=$gate.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$held=$true}}
    $output=Start-Peer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.RuneboundReviewGameMode?listen';$hostProcess=$output[-1]
    $output | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(4);$ready=$false
    while([DateTime]::UtcNow -lt $deadline){
        if((Test-Path -LiteralPath "$runDir/host.log") -and (Select-String -LiteralPath "$runDir/host.log" -SimpleMatch 'RUNEBOUND_WIRE_HOST_READY' -Quiet)){$ready=$true;break}
        if($hostProcess.HasExited){throw 'Audit host exited during startup'};Start-Sleep -Seconds 1
    }
    if(-not $ready){throw 'Audit host startup timeout'}
    $output=Start-Peer 'client' ('127.0.0.1:'+$port);$output | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(3)
    while([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath "$runDir/host.json")){
        if($hostProcess.HasExited){throw 'Audit host exited before result'};Start-Sleep -Seconds 1
    }
    if(-not (Test-Path -LiteralPath "$runDir/host.json")){throw 'Audit result timeout'}
    $report=Get-Content -LiteralPath "$runDir/host.json" -Raw | ConvertFrom-Json
    @{directory=$runDir;passed=$report.passed;transport='real local UDP listen host + client';port=$port;packet_lag_ms=80;packet_loss_percent=2;rendered=$false;world_body_suppressed=$true;pids=@($owned | ForEach-Object {$_.Id})} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/wire-receipt.json" -Encoding utf8
    Write-Output "RUNEBOUND_WIRE_FINISHED PASS=$($report.passed) PATH=$runDir"
    if(-not $report.passed){exit 1}
} finally {
    foreach($p in $owned){
        if(-not $p.HasExited){[void]$p.WaitForExit(5000)}
        if(-not $p.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-RuneboundReviewWire*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}
        }
    }
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
