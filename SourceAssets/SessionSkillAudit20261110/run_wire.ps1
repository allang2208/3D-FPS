param([ValidateSet('ChainSlash','PojunChain','PojunLeap','HammerLeap','PojunSlam','HammerSlam','Conversation','StarMarrow','FlameArmor')][string]$Case='ChainSlash',[switch]$Dedicated,[switch]$Observer,[string]$ProjectRoot='D:/FPS3D/FPSGAME')
$ErrorActionPreference='Stop'
if($Observer -and ($Case -ne 'PojunChain' -or !$Dedicated)){throw 'The independent observer requires PojunChain on a dedicated server.'}
$project=$ProjectRoot;$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss';$mode=if($Dedicated){'dedicated'}else{'listen'}
$run=Join-Path $PSScriptRoot ('Wire/'+$Case+'-'+$mode+'-'+$stamp)
New-Item -ItemType Directory -Force -Path $run | Out-Null
$port=20060;while(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){$port++}
$flag=switch($Case){ChainSlash{'-SessionChainWire'}PojunChain{'-SessionChainWire'}PojunLeap{'-LeapMovementWire'}HammerLeap{'-LeapMovementWire'}PojunSlam{'-LeapMovementWire'}HammerSlam{'-LeapMovementWire'}Conversation{'-ConversationCombatWire'}StarMarrow{'-StarMarrowWireAudit'}FlameArmor{'-FlameArmorWireAudit'}}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-Peer([string]$role,[string]$map){
    $args=@(('"'+$project+'/FPSGAME.uproject"'),('"'+$map+'"'),'-nullrhi','-nosound','-unattended','-nosplash','-Multiprocess','-NoLiveCoding','-SkillWireAudit',$flag,
        '-PktLag=80','-PktLoss=2',('-ColdSteelProfile=SkillNetworkAudit_Conversation_'+$stamp+'_'+$role),('-port='+$port),
        ('-UserDir="'+$run+'/'+$role+'/"'),('-SkillWireOutput="'+$run+'/'+$role+'.json"'),('-abslog="'+$run+'/'+$role+'.log"'),'-ExecCmds="t.MaxFPS 30"',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False')
    if($Case -like 'Pojun*'){$args+='-PojunWire'}
    if($Case -like '*Slam'){$args+='-ChargedSlamWire'}
    if($Case -like '*Slam' -and $role -eq 'client'){$args+='-testexit="Host closed the connection."'}
    if($Observer){$args+='-PojunObserverWire'}
    if($role -eq 'observer'){$args+='-PojunPassiveObserver'}
    if($Case -like 'Pojun*' -or $flag -eq '-LeapMovementWire'){
        $args+=@('-NoAssetRegistryCacheWrite','-NoShaderCompile','-AssetGatherAll=false','-DisablePython','-DPCVars=fps.body.AsyncPreload=0,Editor.AsyncSkinnedAssetCompilation=0,Editor.AsyncStaticMeshCompilation=0')
        $cache=Join-Path $run "$role/Intermediate/CachedAssetRegistry"
        New-Item -ItemType Directory -Path $cache -Force | Out-Null
        $discovery=Join-Path $project 'Intermediate/CachedAssetRegistryDiscovery.bin'
        if(Test-Path -LiteralPath $discovery){Copy-Item -LiteralPath $discovery -Destination (Split-Path $cache -Parent)}
        foreach($entry in (Get-ChildItem -LiteralPath (Join-Path $project 'Intermediate/CachedAssetRegistry') -File -ErrorAction SilentlyContinue)){
            if($entry.Extension -eq '.bin' -and [IO.Path]::GetPathRoot($entry.FullName) -eq [IO.Path]::GetPathRoot($cache)){
                New-Item -ItemType HardLink -Path (Join-Path $cache $entry.Name) -Target $entry.FullName | Out-Null
            }else{Copy-Item -LiteralPath $entry.FullName -Destination $cache}
        }
    }
    if($role -eq 'host' -and $Dedicated){$args+=@('-server','-StarDedicatedAudit')}else{$args+='-game'}
    $p=Start-Process -FilePath $exe -ArgumentList $args -WindowStyle Hidden -PassThru;$owned.Add($p)
    @{pid=$p.Id;role=$role;arguments=$args} | ConvertTo-Json | Set-Content -LiteralPath "$run/launch-$role.json" -Encoding utf8
    Write-Output "WIRE_PEER $Case $mode $role PID=$($p.Id)";return $p
}
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no peers started.'}
    if($Case -notlike 'Pojun*' -and $flag -ne '-LeapMovementWire' -and (Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue)){throw 'Existing UE process preserved.'}
    $map='/Engine/Maps/Entry?game=/Script/FPSGAME.SkillWireAuditGameMode';if(-not $Dedicated){$map+='?listen'}
    $launch=Start-Peer 'host' $map;$server=$launch[-1];$launch | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    do{
        if($server.HasExited){throw 'Host exited before ready.'}
        if([DateTime]::UtcNow -gt $deadline){throw 'Host startup timeout.'}
        Start-Sleep -Seconds 1
    }until((Test-Path -LiteralPath "$run/host.log") -and (Select-String -LiteralPath "$run/host.log" -SimpleMatch 'SKILL_WIRE_HOST_READY' -Quiet))
    if($Observer){
        $launch=Start-Peer 'observer' ('127.0.0.1:'+$port);$passive=$launch[-1]
        $deadline=[DateTime]::UtcNow.AddMinutes(8)
        do{
            if($server.HasExited -or $passive.HasExited -or [DateTime]::UtcNow -gt $deadline){throw 'Observer failed to join.'}
            Start-Sleep -Seconds 1
        }until(Select-String -LiteralPath "$run/host.log" -SimpleMatch 'POJUN_WIRE_OBSERVER_JOINED' -Quiet)
    }
    $launch=Start-Peer 'client' ('127.0.0.1:'+$port);$launch | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(18)
    while($true){
        if(Test-Path -LiteralPath "$run/host.json"){
            if($flag -ne '-LeapMovementWire'){break}
            try{if((Get-Content -Raw -LiteralPath "$run/host.json" | ConvertFrom-Json).complete){break}}catch {if($server.HasExited){throw}}
        }
        if($server.HasExited){throw 'Host exited before result.'}
        if([DateTime]::UtcNow -gt $deadline){throw 'Network review timed out.'}
        Start-Sleep -Seconds 1
    }
    $exits=@();foreach($p in $owned){if(-not $p.WaitForExit(30000)){throw "Peer $($p.Id) failed to exit normally."};$exits+=@{pid=$p.Id;exit_code=$p.ExitCode}}
    $result=Get-Content -LiteralPath "$run/host.json" -Raw | ConvertFrom-Json
    $clientPassed=Test-Path -LiteralPath "$run/client.json"
    if($clientPassed){
        $clientResult=Get-Content -Raw -LiteralPath "$run/client.json" | ConvertFrom-Json
        if($clientResult.PSObject.Properties['passed']){$clientPassed=$clientResult.passed}
    }
    $passed=$result.passed -and $clientPassed -and -not @($exits | Where-Object {$_.exit_code -ne 0}).Count
    if($Observer){$passed=$passed -and (Test-Path -LiteralPath "$run/observer.json") -and (Get-Content -Raw -LiteralPath "$run/observer.json" | ConvertFrom-Json).passed}
    @{passed=$passed;case=$Case;mode=$mode;run=$run;port=$port;configured_lag_ms=80;configured_loss_percent=2;rendered=$false;peer_exits=$exits} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$run/receipt.json" -Encoding utf8
    Write-Output "WIRE_DONE PASS=$passed PATH=$run"
    if(-not $passed){exit 1}
}finally{
    foreach($p in $owned){if(-not $p.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)";
        if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-SkillWireAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}}}
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
