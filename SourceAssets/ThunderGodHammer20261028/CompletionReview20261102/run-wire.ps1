param([ValidateSet('Listen','Dedicated')][string]$Mode='Listen')
$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME';$exe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss';$run=Join-Path $PSScriptRoot ($Mode+'-'+$stamp)
New-Item -ItemType Directory -Force -Path $run | Out-Null
$port=20841;while(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){$port++}
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
function Start-Peer([string]$role,[string]$map){
    $args=@(('"'+$project+'\FPSGAME.uproject"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-NoLiveCoding','-AssetGatherAll=false','-ThunderHammerWireAudit',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=SkillNetworkAudit_Thunder_'+$stamp+'_'+$role),('-port='+$port),
        ('-UserDir="'+$run.Replace('\','/')+'/'+$role+'/"'),('-ThunderWireOutput="'+$run+'\'+$role+'.json"'),
        ('-abslog="'+$run+'\'+$role+'.log"'),'-ExecCmds="t.MaxFPS 30"')
    if($role -eq 'host' -and $Mode -eq 'Dedicated'){$args+='-server'}
    if($role -eq 'observer'){$args+='-ThunderWireObserver'}
    $p=Start-Process -FilePath $exe -ArgumentList $args -WindowStyle Hidden -PassThru;$owned.Add($p)
    @{role=$role;pid=$p.Id;arguments=$args}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath ($run+'\launch-'+$role+'.json') -Encoding utf8
    Write-Output "THUNDER_PEER $role PID=$($p.Id)";return $p
}
function Wait-Marker([string]$marker,[System.Diagnostics.Process]$peer,[int]$seconds=360){
    $deadline=(Get-Date).AddSeconds($seconds)
    do {
        if((Test-Path -LiteralPath ($run+'\host.log')) -and (Select-String -LiteralPath ($run+'\host.log') -SimpleMatch $marker -Quiet)){return}
        if($peer.HasExited){throw "Host exited before $marker"}
        if((Get-Date) -gt $deadline){throw "Timed out before $marker"}
        Start-Sleep -Seconds 2
    }while($true)
}
try {
    for($attempt=0;$attempt -lt 20 -and -not $held;$attempt++){
        try{$held=$gate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$held=$true}
        if(-not $held){Write-Output 'Waiting for existing UE batch.'}
    }
    if(-not $held){throw 'UE batch occupied; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Existing build preserved.'}
    $map='/Engine/Maps/Entry?game=/Script/FPSGAME.ThunderHammerWireGameMode';if($Mode -eq 'Listen'){$map+='?listen'}
    $hostOut=Start-Peer 'host' $map;$hostPeer=$hostOut[-1];$hostOut|Where-Object {$_ -is [string]}|Write-Output
    Wait-Marker 'THUNDER_WIRE_HOST_READY' $hostPeer
    $clientOut=Start-Peer 'client' ('127.0.0.1:'+$port);$clientOut|Where-Object {$_ -is [string]}|Write-Output
    Wait-Marker 'THUNDER_WIRE_GUEST_JOINED' $hostPeer
    $observerOut=Start-Peer 'observer' ('127.0.0.1:'+$port);$observerOut|Where-Object {$_ -is [string]}|Write-Output
    Wait-Marker 'THUNDER_WIRE_FINISHED' $hostPeer
    $exits=@();foreach($p in $owned){if(-not $p.WaitForExit(30000)){throw "Peer $($p.Id) did not exit"};$exits+=@{pid=$p.Id;exit_code=$p.ExitCode}}
    $result=Get-Content -LiteralPath ($run+'\host.json') -Raw|ConvertFrom-Json
    $ok=$result.passed -and -not @($exits|Where-Object {$_.exit_code -ne 0}).Count
    @{passed=$ok;run=$run;mode=$Mode;rendered=$false;peer_exits=$exits;configured_lag_ms_each_peer=60;configured_loss_percent_each_peer=3;port=$port}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath ($run+'\receipt.json') -Encoding utf8
    Write-Output "THUNDER_WIRE_DONE PASS=$ok PATH=$run";if(-not $ok){exit 1}
} finally {
    foreach($p in $owned){if(-not $p.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)";if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-ThunderHammerWireAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}}}
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
