$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME/SourceAssets/Super90AttachmentAudit20261016'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$runDir=Join-Path $root ('Wire/'+$stamp)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$port=19867
if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Shotgun audit port occupied'}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-Peer([string]$role,[string]$map){
    $args=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-ShotgunWireAudit',('-ColdSteelProfile=ShotgunWireAudit_'+$stamp+'_'+$role),('-port='+$port),
        ('-ShotgunWireOutput="'+(Join-Path $runDir ($role+'.json'))+'"'),('-abslog="'+(Join-Path $runDir ($role+'.log'))+'"'),'-ExecCmds="t.MaxFPS 30"')
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
    $owned.Add($p);Write-Output "SHOTGUN_PEER_STARTED $role PID=$($p.Id)";return $p
}
try{
    try{$held=$gate.WaitOne(1200000)}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){exit 75}
    $hostOutput=Start-Peer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ShotgunWireAuditGameMode?listen';$hostProcess=$hostOutput[-1]
    $hostOutput | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(4)
    $ready=$false
    while([DateTime]::UtcNow -lt $deadline){
        if((Test-Path -LiteralPath "$runDir/host.log") -and (Select-String -LiteralPath "$runDir/host.log" -SimpleMatch 'SHOTGUN_WIRE_HOST_READY' -Quiet)){$ready=$true;break}
        if($hostProcess.HasExited){throw 'Audit host exited during startup'}
        Start-Sleep -Seconds 1
    }
    if(-not $ready){throw 'Audit host startup timeout'}
    $clientOutput=Start-Peer 'client' ('127.0.0.1:'+$port);$clientOutput | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(5)
    while([DateTime]::UtcNow -lt $deadline -and -not (Test-Path -LiteralPath "$runDir/host.json")){
        if($hostProcess.HasExited){throw 'Audit host exited before result'}
        Start-Sleep -Seconds 1
    }
    if(-not (Test-Path -LiteralPath "$runDir/host.json")){throw 'Shotgun audit result timeout'}
    $report=Get-Content -LiteralPath "$runDir/host.json" -Raw | ConvertFrom-Json
    @{directory=$runDir;passed=$report.passed;transport='real local UDP listen host + client';port=$port} | ConvertTo-Json | Set-Content -LiteralPath "$root/wire_receipt.json" -Encoding utf8
    Write-Output "SHOTGUN_WIRE_FINISHED PASS=$($report.passed) PATH=$runDir"
    if(-not $report.passed){exit 1}
}finally{
    foreach($p in $owned){
        if(-not $p.HasExited){[void]$p.WaitForExit(5000)}
        if(-not $p.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-ShotgunWireAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}
        }
    }
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
