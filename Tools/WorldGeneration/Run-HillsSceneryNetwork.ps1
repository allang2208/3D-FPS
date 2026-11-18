param([string]$Attempt=(Get-Date -Format 'yyyyMMdd-HHmmss'),[string]$BuildBatch='HillsClosure20261118R2')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$run=Join-Path $project ('Saved/HillsSceneryNetwork20261118/'+$Attempt)
$hostDir=Join-Path $run 'Host'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[Collections.Generic.List[Diagnostics.Process]]::new();$port=20218
function Launch([string]$Role,[string]$Map,[switch]$Rejoin,[switch]$Mismatch){
    $dir=Join-Path $run $Role;New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $label=if($Rejoin){'rejoin'}else{$Role}
    $arguments=@(('"'+$hostDir+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-HillsSceneryNetworkProbe','-SkipStartupMenu','-ClearwaterNoMenu',
        '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',('-port='+$port),
        ('-ColdSteelProfile=HillsScenery_'+$Attempt+'_'+$Role),('-UserDir="'+$dir+'"'),('-abslog="'+$run+'/'+$label+'.log"'),
        ('-HillsSceneryOutput="'+$run+'/Evidence"'),'-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
        '-ExecCmds="t.MaxFPS 45,fps.body.WorldBodySuppress 1,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,fps.Test.HillsSceneryNetworkProbe"',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    if($Mismatch){$arguments+='-HillsCompatibilityMismatch'}
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $peerHandle=$p.Handle
    $owned.Add($p);@{pid=$p.Id;args=$arguments;role=$label}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$run/launch-$label.json"
    Write-Host "HILLS_SCENERY_STARTED $label pid=$($p.Id)";return $p
}
function Marker([string]$Text,[Diagnostics.Process]$Peer,[int]$Seconds=900){
    $end=[DateTime]::UtcNow.AddSeconds($Seconds)
    while([DateTime]::UtcNow -lt $end){
        if(Test-Path -LiteralPath "$run/Evidence/result.json"){throw 'Probe finished before milestone; inspect result.json'}
        if((Test-Path -LiteralPath "$run/host.log") -and (Select-String -LiteralPath "$run/host.log" -SimpleMatch $Text -Quiet)){return}
        if($Peer.HasExited){throw "Peer exited before $Text"};Start-Sleep -Seconds 2
    };throw "Timeout waiting for $Text"
}
function Stop-Owned([Diagnostics.Process]$P){
    if($P.HasExited){return};$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($P.Id)"
    if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($hostDir) -and $live.CommandLine.Contains('-HillsSceneryNetworkProbe')){Stop-Process -Id $P.Id -ErrorAction SilentlyContinue;[void]$P.WaitForExit(10000)}
}
try{
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    if(Test-Path -LiteralPath $run){throw 'Attempt already exists'}
    if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Port occupied'}
    New-Item -ItemType Directory -Force -Path "$hostDir/Binaries/Win64","$hostDir/Saved/SaveGames","$run/Evidence"|Out-Null
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostDir/FPSGAME.uproject"
    Copy-Item -LiteralPath "$project/Config" -Destination "$hostDir/Config" -Recurse
    foreach($folder in 'Content','Plugins','Shaders'){New-Item -ItemType Junction -Path "$hostDir/$folder" -Target "$project/$folder"|Out-Null}
    New-Item -ItemType Directory -Force -Path "$hostDir/Intermediate"|Out-Null
    foreach($cache in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){
        if(Test-Path -LiteralPath "$project/Intermediate/$cache"){Copy-Item -LiteralPath "$project/Intermediate/$cache" -Destination "$hostDir/Intermediate/$cache" -Recurse}
    }
    $build=Get-Content -LiteralPath "$project/SourceAssets/$BuildBatch/build.json" -Raw|ConvertFrom-Json
    if(-not $build.finished -or @($build.targets|Where-Object {$_.exit_code -ne 0}).Count){throw 'Requested build is incomplete'}
    foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$project/SourceAssets/$BuildBatch/Module/$file" -Destination "$hostDir/Binaries/Win64/$file"}
    $save="$project/Saved/SaveGames/TemperateHills_World.sav";$saveHash=(Get-FileHash -LiteralPath $save).Hash
    Copy-Item -LiteralPath $save -Destination "$hostDir/Saved/SaveGames/TemperateHills_World.sav"
    $hostPeer=Launch 'host' '/Game/GameMaps/L_TemperateHills_Initial?listen?HillsContinue'
    Marker 'GameNetDriver' $hostPeer
    $bad=Launch 'mismatch' ('127.0.0.1:'+$port) -Mismatch
    $end=[DateTime]::UtcNow.AddMinutes(4);$rejected=$false
    while([DateTime]::UtcNow -lt $end){
        if((Select-String -LiteralPath "$run/host.log" -Pattern 'Client connecting with invalid version|incompatible.*version' -Quiet) -or
            ((Test-Path -LiteralPath "$run/mismatch.log") -and (Select-String -LiteralPath "$run/mismatch.log" -Pattern 'Server is incompatible with the local version' -Quiet))){$rejected=$true;break}
        if($hostPeer.HasExited){throw 'Host exited during mismatch case'};Start-Sleep -Seconds 2
    }
    Stop-Owned $bad
    @{passed=$rejected;case='content_mismatch_rejected_before_join'}|ConvertTo-Json|Set-Content -LiteralPath "$run/Evidence/mismatch.json"
    if(-not $rejected){throw 'Mismatch rejection was not observed'}
    $client=Launch 'client' ('127.0.0.1:'+$port)
    Marker 'HILLS_SCENERY_DISCONNECT_CLIENT' $hostPeer 1400
    Stop-Owned $client
    @{pid=$client.Id;expected_forced_disconnect=$true;exit_code=$client.ExitCode}|ConvertTo-Json|Set-Content -LiteralPath "$run/exit-client.json"
    Marker 'HILLS_SCENERY_RECONNECT_READY' $hostPeer 180
    $rejoin=Launch 'client' ('127.0.0.1:'+$port) -Rejoin
    $end=[DateTime]::UtcNow.AddMinutes(8)
    while(-not(Test-Path -LiteralPath "$run/Evidence/result.json")){
        if($hostPeer.HasExited -or [DateTime]::UtcNow -gt $end){throw 'Missing completion receipt'};Start-Sleep -Seconds 2
    }
    $cleanExit=$true
    foreach($pair in @(@('host',$hostPeer),@('rejoin',$rejoin))){
        $p=$pair[1];[void]$p.WaitForExit(15000);@{pid=$p.Id;exited=$p.HasExited;exit_code=$p.ExitCode}|ConvertTo-Json|Set-Content -LiteralPath "$run/exit-$($pair[0]).json"
        $cleanExit=$cleanExit -and $p.HasExited -and ($p.ExitCode -eq 0)
    }
    $r=Get-Content -LiteralPath "$run/Evidence/result.json" -Raw|ConvertFrom-Json
    $passed=$r.passed -and $rejected -and $cleanExit
    @{passed=$passed;cases=($r.checks.Count+1);clean_exit=$cleanExit;module_sha256=(Get-FileHash -LiteralPath "$hostDir/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;source_save_unchanged=((Get-FileHash -LiteralPath $save).Hash -eq $saveHash);lag_ms=60;loss_percent=2;rendered=$false}|ConvertTo-Json|Set-Content -LiteralPath "$run/summary.json"
    Write-Output "HILLS_SCENERY_DONE passed=$passed run=$run"
    if(-not $passed){throw 'Scenery network checks or process shutdown failed'}
}finally{foreach($p in $owned){Stop-Owned $p};if($held){$gate.ReleaseMutex()};$gate.Dispose()}
