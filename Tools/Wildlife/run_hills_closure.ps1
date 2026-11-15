param([string]$Attempt=(Get-Date -Format 'yyyyMMdd-HHmmss'))
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$run=Join-Path $project ('Saved/HillsMultiplayerClosure20261115/'+$Attempt)
$hostDir=Join-Path $run 'Host'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[Collections.Generic.List[Diagnostics.Process]]::new()
$port=20215
function Launch([string]$Role,[string]$Map,[switch]$Rejoin){
    $dir=Join-Path $run $Role;New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $label=if($Rejoin){'rejoin'}else{$Role}
    $args=@(('"'+$hostDir+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-HillsMultiplayerClosure','-SkipStartupMenu','-ClearwaterNoMenu','-HillsNewWorld','-HillsSeed=122',
        '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',('-port='+$port),
        ('-ColdSteelProfile=HillsClosure_'+$Attempt+'_'+$Role),('-UserDir="'+$dir+'"'),('-abslog="'+$run+'/'+$label+'.log"'),
        ('-HillsClosureOutput="'+$run+'/Evidence"'),'-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
        '-ExecCmds="t.MaxFPS 45,fps.body.WorldBodySuppress 1,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,fps.Test.HillsMultiplayerClosure"',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
    $owned.Add($p);@{pid=$p.Id;args=$args;role=$label} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$run/launch-$label.json"
    Write-Host "HILLS_CLOSURE_STARTED $label pid=$($p.Id)";return $p
}
function Marker([string]$Text,[Diagnostics.Process]$Peer,[int]$Seconds=600){
    $end=[DateTime]::UtcNow.AddSeconds($Seconds)
    while([DateTime]::UtcNow -lt $end){
        if(Test-Path -LiteralPath "$run/Evidence/result.json"){throw 'Probe finished before requested milestone; inspect Evidence/result.json'}
        if((Test-Path -LiteralPath "$run/host.log") -and (Select-String -LiteralPath "$run/host.log" -SimpleMatch $Text -Quiet)){return}
        if($Peer.HasExited){throw "Peer exited before $Text"};Start-Sleep -Seconds 2
    };throw "Timeout waiting for $Text"
}
function Stop-Owned([Diagnostics.Process]$P){
    if($P.HasExited){return};$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($P.Id)"
    if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($hostDir) -and $live.CommandLine.Contains('-HillsMultiplayerClosure')){Stop-Process -Id $P.Id -ErrorAction SilentlyContinue;[void]$P.WaitForExit(10000)}
}
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'Shared runtime queue timeout'}
    $end=[DateTime]::UtcNow.AddMinutes(10)
    while(@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}).Count){if([DateTime]::UtcNow -gt $end){throw 'Another build still active'};Start-Sleep -Seconds 3}
    $build=Get-Content -LiteralPath "$project/Saved/HillsMultiplayerClosure20261115/build-FPSGAMEEditor.json" -Raw | ConvertFrom-Json
    if($build.exit_code -ne 0){throw 'This closure build did not succeed; do not run an older module'}
    if(Test-Path -LiteralPath $run){throw 'Attempt already exists'}
    if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Port occupied'}
    New-Item -ItemType Directory -Force -Path "$hostDir/Binaries/Win64","$run/Evidence" | Out-Null
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostDir/FPSGAME.uproject"
    Copy-Item -LiteralPath "$project/Config" -Destination "$hostDir/Config" -Recurse
    foreach($folder in 'Content','Plugins','Shaders'){New-Item -ItemType Junction -Path "$hostDir/$folder" -Target "$project/$folder" | Out-Null}
    New-Item -ItemType Directory -Force -Path "$hostDir/Intermediate" | Out-Null
    foreach($cache in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){
        if(Test-Path -LiteralPath "$project/Intermediate/$cache"){Copy-Item -LiteralPath "$project/Intermediate/$cache" -Destination "$hostDir/Intermediate/$cache" -Recurse}
    }
    foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$project/Binaries/Win64/$file" -Destination "$hostDir/Binaries/Win64/$file"}
    $hostPeer=Launch 'host' '/Game/GameMaps/L_TemperateHills_Initial?listen'
    Marker 'GameNetDriver' $hostPeer
    $client=Launch 'client' ('127.0.0.1:'+$port)
    Marker 'HILLS_CLOSURE_DISCONNECT_CLIENT' $hostPeer 720
    Stop-Owned $client
    @{pid=$client.Id;expected_forced_disconnect=$true;exit_code=$client.ExitCode} | ConvertTo-Json | Set-Content -LiteralPath "$run/exit-client.json"
    Marker 'HILLS_CLOSURE_RECONNECT_READY' $hostPeer 180
    $rejoin=Launch 'client' ('127.0.0.1:'+$port) -Rejoin
    $end=[DateTime]::UtcNow.AddMinutes(12)
    while(-not (Test-Path -LiteralPath "$run/Evidence/result.json")){
        if($hostPeer.HasExited -or [DateTime]::UtcNow -gt $end){throw 'Missing completion receipt'};Start-Sleep -Seconds 2
    }
    foreach($pair in @(@('host',$hostPeer),@('rejoin',$rejoin))){
        $p=$pair[1];[void]$p.WaitForExit(15000);@{pid=$p.Id;exited=$p.HasExited;exit_code=$p.ExitCode} | ConvertTo-Json | Set-Content -LiteralPath "$run/exit-$($pair[0]).json"
    }
    $r=Get-Content -LiteralPath "$run/Evidence/result.json" -Raw | ConvertFrom-Json
    @{passed=$r.passed;cases=$r.checks.Count;module_sha256=(Get-FileHash -LiteralPath "$hostDir/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;lag_ms=60;loss_percent=2;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$run/summary.json"
    Write-Output "HILLS_CLOSURE_DONE passed=$($r.passed) cases=$($r.checks.Count) run=$run"
}finally{
    foreach($p in $owned){Stop-Owned $p};if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
