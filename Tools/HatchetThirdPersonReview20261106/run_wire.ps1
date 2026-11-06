param([ValidateSet('Listen','Dedicated')][string]$Mode='Listen',[switch]$Render,[ValidateSet('jason','kaitlin')][string]$Head='jason',[switch]$Hitch,[ValidateRange(0,8)][int]$HeavyCycles=0,[ValidateRange(0,800)][int]$ChargeLagMs=0,[ValidateSet('','Falcon','Ghost')][string]$Legend='',[switch]$Viewer,[switch]$SplitTargets)
$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$exe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$run=Join-Path $PSScriptRoot ($Mode+'-'+$stamp)
New-Item -ItemType Directory -Force -Path $run | Out-Null
$port=19937
while(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){$port++}
$profileId=[guid]::NewGuid().ToString()
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$oldSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Start-Peer([string]$role,[string]$map){
    $commands='t.MaxFPS 30'
    $peerProfile=if($role -eq 'viewer'){[guid]::NewGuid().ToString()}else{$profileId}
    if($Render -and $role -eq 'host'){$commands+=',r.DynamicGlobalIlluminationMethod 0,r.ReflectionMethod 0,r.Shadow.Virtual.Enable 0,r.ShadowQuality 0,r.MotionBlurQuality 0,r.ScreenPercentage 75'}
    $args=@(('"'+$project+'\FPSGAME.uproject"'),('"'+$map+'"'),'-game','-nosound','-unattended','-nosplash','-NoLiveCoding','-AssetGatherAll=false','-KukriCombatWireAudit','-HatchetCombatWireAudit','-KukriHeavyNetTrace','-KukriWireNoOutfit',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False','-KukriRiftTrace',
        ('-ColdSteelProfile=KukriWireAudit_'+$stamp+'_'+$role),('-KukriProfileId='+$peerProfile),('-KukriWireHead='+$Head),('-port='+$port),
        ('-UserDir="'+$run.Replace('\','/')+'/'+$role+'/"'),('-KukriWireOutput="'+$run+'\'+$role+'.json"'),
        ('-abslog="'+$run+'\'+$role+'.log"'),('-ExecCmds="'+$commands+'"'))
    if($Hitch){$args+='-KukriWireHitch'}
    if($Legend){$args+=('-HatchetLegend='+$Legend)}
    if($SplitTargets){$args+='-HatchetSplitTargets'}
    if($role -eq 'viewer'){$args+='-HatchetWatchOnly'}
    $args+='-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
    if($HeavyCycles){$args+=('-KukriWireHeavyCycles='+$HeavyCycles)}
    if($ChargeLagMs){$args+=('-KukriChargeLagMs='+$ChargeLagMs)}
    if($Render){$args+='-KukriWireVisualSlow'}
    if($role -eq 'host' -and $Mode -eq 'Dedicated'){$args+='-server'}
    if($Render -and $role -eq 'host'){$args+=@('-RenderOffscreen','-ResX=1280','-ResY=720',('-KukriWireCapture="'+$run+'\Frames"'))}
    else{$args+='-nullrhi'}
    $p=Start-Process -FilePath $exe -ArgumentList $args -WindowStyle Hidden -PassThru
    $owned.Add($p)
    @{role=$role;pid=$p.Id;arguments=$args} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath ($run+'\launch-'+$role+'.json') -Encoding utf8
    Write-Output "KUKRI_PEER $role PID=$($p.Id)"
    return $p
}
function Wait-Marker([string]$marker,[System.Diagnostics.Process]$peer,[int]$seconds=420){
    $deadline=(Get-Date).AddSeconds($seconds)
    do {
        if((Test-Path -LiteralPath ($run+'\host.log')) -and (Select-String -LiteralPath ($run+'\host.log') -SimpleMatch $marker -Quiet)){return}
        if($peer.HasExited){throw "Host exited before $marker"}
        if((Get-Date) -gt $deadline){throw "Timed out before $marker"}
        Start-Sleep -Seconds 2
    } while($true)
}
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved; nothing started.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Existing build preserved.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $map='/Engine/Maps/Entry?game=/Script/FPSGAME.KukriCombatWireGameMode'
    if($Mode -eq 'Listen'){$map+='?listen'}
    $hostOut=Start-Peer 'host' $map;$hostPeer=$hostOut[-1];$hostOut | Where-Object {$_ -is [string]} | Write-Output
    Wait-Marker 'KUKRI_COMBAT_HOST_READY' $hostPeer
    if($Viewer){
        $viewerOut=Start-Peer 'viewer' ('127.0.0.1:'+$port+'?HatchetViewer=1');$viewerOut | Where-Object {$_ -is [string]} | Write-Output
        Wait-Marker 'HATCHET_VIEWER_READY' $hostPeer
    }
    $clientOut=Start-Peer 'client' ('127.0.0.1:'+$port);$clientPeer=$clientOut[-1];$clientOut | Where-Object {$_ -is [string]} | Write-Output
    Wait-Marker 'KUKRI_COMBAT_REJOIN_READY' $hostPeer 900
    if(-not $clientPeer.WaitForExit(30000)){throw 'First client did not exit normally.'}
    $rejoinOut=Start-Peer 'rejoin' ('127.0.0.1:'+$port);$rejoinOut | Where-Object {$_ -is [string]} | Write-Output
    Wait-Marker 'KUKRI_COMBAT_FINISHED' $hostPeer
    $exits=@()
    foreach($p in $owned){if(-not $p.WaitForExit(30000)){throw "Peer $($p.Id) did not exit normally."};$exits+=@{pid=$p.Id;exit_code=$p.ExitCode}}
    $result=Get-Content -LiteralPath ($run+'\host.json') -Raw | ConvertFrom-Json
    $ok=$result.passed -and -not @($exits | Where-Object {$_.exit_code -ne 0}).Count
    if($Legend){
        $sides=if($Mode -eq 'Dedicated'){@('client')}else{@('client','host')}
        if($Viewer){$sides=@($sides)+@('viewer')}
        $surface=@{}
        foreach($side in $sides){
            $blood=@(Select-String -LiteralPath "$run/$side.log" -Pattern 'HATCHET_WIRE_SURFACE body=1 surface=5 actor=.*NurseZombie.*near_actor=1').Count
            $metal=@(Select-String -LiteralPath "$run/$side.log" -Pattern 'HATCHET_WIRE_SURFACE body=0 surface=0 actor=.*KukriWireMetalWall').Count
            $surface[$side]=@{flesh=$blood;metal_wall=$metal};$ok=$ok -and $blood -gt 0 -and $metal -gt 0
            if($side -eq 'client'){
                $accepted=($result.cases | Where-Object {$_ -ne $null -and $null -ne $_.damage_contacts} | Measure-Object -Property damage_contacts -Sum).Sum
                $surface[$side].accepted_body_hits=$accepted
                $ok=$ok -and $blood -eq $accepted
            }
        }
        if($Legend -eq 'Ghost'){
            $cap=Select-String -LiteralPath "$run/client.log" -SimpleMatch 'HATCHET_GHOST_CLIENT stacks=12' -Quiet
            $expired=Select-String -LiteralPath "$run/client.log" -SimpleMatch 'HATCHET_GHOST_CLIENT stacks=0 previous=12' -Quiet
            $surface['guest_cap_and_expiry']=($cap -and $expired);$ok=$ok -and $cap -and $expired
        }
        $surface | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$run/surface.json" -Encoding utf8
    }
    @{passed=$ok;run=$run;mode=$Mode;rendered=[bool]$Render;head=$Head;outfit='base body; no optional clothing';peer_exits=$exits;configured_lag_ms_each_peer=60;configured_loss_percent_each_peer=3;charge_start_lag_ms=$ChargeLagMs;heavy_cycles=$HeavyCycles;profile_id=$profileId;port=$port} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath ($run+'\receipt.json') -Encoding utf8
    Write-Output "KUKRI_WIRE_DONE PASS=$ok PATH=$run"
    if(-not $ok){exit 1}
} finally {
    foreach($p in $owned){if(-not $p.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)";if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-KukriCombatWireAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}}}
    $env:UE_SKIP_UBT_SDK_SETUP=$oldSdk;if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
