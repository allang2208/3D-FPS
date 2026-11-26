param(
    [string]$Attempt=(Get-Date -Format 'yyyyMMdd-HHmmss'),
    [string]$Build,
    [switch]$Construction,
    [ValidateRange(1024,65535)][int]$Port=20318
)
$ErrorActionPreference='Stop'
$auditProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$auditRun=Join-Path $auditProject ('Saved/VillageNetworkAudit20261118/'+$Attempt)
$auditHost=Join-Path $auditRun 'Host'
$auditPort=$Port
$auditMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$auditHeld=$false
$auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
function Start-AuditPeer([string]$Role,[string]$Map,[switch]$Rejoin) {
    $peerDir=Join-Path $auditRun $Role
    New-Item -ItemType Directory -Force -Path $peerDir | Out-Null
    $label=if($Rejoin){'rejoin'}else{$Role}
    $peerArgs=@(('"'+$auditHost+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-NoShaderCompile','-NoLiveCoding','-nosound','-unattended','-nosplash',
        '-VillageNetworkAudit','-SkipStartupMenu','-ClearwaterNoMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-port='+$auditPort),('-ColdSteelProfile=VillageNetworkAudit_'+$Attempt+'_'+$Role),('-UserDir="'+$peerDir+'"'),
        ('-abslog="'+$auditRun+'/'+$label+'.log"'),('-VillageNetworkOutput="'+$auditRun+'/Evidence"'),
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
        '-ExecCmds="t.MaxFPS 40,fps.body.WorldBodySuppress 1,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,fps.Test.VillageNetworkAudit"',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
        '-ini:Game:[TemperateHills.NightRaid]:Enabled=False',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    if($Construction){$peerArgs+='-VillageConstructionAudit'}
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $peerHandle=$peer.Handle
    $auditOwned.Add($peer)
    @{pid=$peer.Id;args=$peerArgs;role=$label}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath "$auditRun/launch-$label.json"
    Write-Host "VILLAGE_NET_STARTED $label pid=$($peer.Id)"
    return $peer
}
function Wait-AuditMarker([string]$Marker,[Diagnostics.Process]$Peer,[int]$Seconds=1500,[Diagnostics.Process]$Guest) {
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    while([DateTime]::UtcNow -lt $deadline) {
        if(Test-Path -LiteralPath "$auditRun/Evidence/result.json"){throw "Probe finished before $Marker; inspect result.json"}
        if((Test-Path -LiteralPath "$auditRun/host.log") -and (Select-String -LiteralPath "$auditRun/host.log" -SimpleMatch $Marker -Quiet)){return}
        if($Peer.HasExited){throw "Host exited before $Marker"}
        if($Guest -and $Guest.HasExited){throw "Guest exited before $Marker (code $($Guest.ExitCode))"}
        Start-Sleep -Seconds 2
    }
    throw "Timeout waiting for $Marker"
}
function Stop-AuditPeer([Diagnostics.Process]$Peer) {
    if($Peer.HasExited){return}
    $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($Peer.Id)"
    if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($auditHost) -and $live.CommandLine.Contains('-VillageNetworkAudit')) {
        Stop-Process -Id $Peer.Id
        [void]$Peer.WaitForExit(10000)
    }
}
try {
    try {$auditHeld=$auditMutex.WaitOne()}catch [Threading.AbandonedMutexException]{$auditHeld=$true}
    if ($Build) {
        foreach($target in 'FPSGAMEEditor','FPSGAME') {
            $receipt=Get-Content -LiteralPath "$Build/$target-build.json" -Raw | ConvertFrom-Json
            if($receipt.exit_code -ne 0){throw "$target build failed"}
        }
        $sourceReceipt=Get-Content -LiteralPath "$Build/sources.json" -Raw | ConvertFrom-Json
        foreach($source in $sourceReceipt.files) {
            if((Get-FileHash -LiteralPath (Join-Path $auditProject $source.path)).Hash -ne $source.sha256) {
                throw "Source changed after build input snapshot: $($source.path)"
            }
        }
    }
    if(Test-Path -LiteralPath $auditRun){throw 'Attempt already exists'}
    if(Get-NetUDPEndpoint -LocalPort $auditPort -ErrorAction SilentlyContinue){throw 'Test port occupied'}
    New-Item -ItemType Directory -Force -Path "$auditHost/Binaries/Win64","$auditHost/Saved/SaveGames","$auditRun/Evidence" | Out-Null
    Copy-Item -LiteralPath "$auditProject/FPSGAME.uproject" -Destination "$auditHost/FPSGAME.uproject"
    Copy-Item -LiteralPath "$auditProject/Config" -Destination "$auditHost/Config" -Recurse
    foreach($folder in 'Content','Shaders') {New-Item -ItemType Junction -Path "$auditHost/$folder" -Target "$auditProject/$folder" | Out-Null}
    # A headless peer must not hold the project's networking DLL open during other builds.
    New-Item -ItemType Directory -Path "$auditHost/Plugins/ColdSteelNet/Binaries/Win64" -Force | Out-Null
    foreach($plugin in Get-ChildItem -LiteralPath "$auditProject/Plugins" -Directory) {
        if($plugin.Name -ne 'ColdSteelNet') {
            New-Item -ItemType Junction -Path "$auditHost/Plugins/$($plugin.Name)" -Target $plugin.FullName | Out-Null
        }
    }
    Copy-Item -LiteralPath "$auditProject/Plugins/ColdSteelNet/ColdSteelNet.uplugin" -Destination "$auditHost/Plugins/ColdSteelNet"
    foreach($file in 'UnrealEditor-ColdSteelNet.dll','UnrealEditor.modules') {
        Copy-Item -LiteralPath "$auditProject/Plugins/ColdSteelNet/Binaries/Win64/$file" -Destination "$auditHost/Plugins/ColdSteelNet/Binaries/Win64"
    }
    New-Item -ItemType Directory -Force -Path "$auditHost/Intermediate" | Out-Null
    foreach($cache in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin') {
        if(Test-Path -LiteralPath "$auditProject/Intermediate/$cache") {Copy-Item -LiteralPath "$auditProject/Intermediate/$cache" -Destination "$auditHost/Intermediate/$cache" -Recurse}
    }
    $manifest='UnrealEditor.modules'
    Copy-Item -LiteralPath "$auditProject/Binaries/Win64/$manifest" -Destination "$auditHost/Binaries/Win64/$manifest"
    $moduleMap=Get-Content -LiteralPath "$auditHost/Binaries/Win64/$manifest" -Raw | ConvertFrom-Json
    foreach ($entry in $moduleMap.Modules.PSObject.Properties) {
        Copy-Item -LiteralPath (Join-Path "$auditProject/Binaries/Win64" $entry.Value) -Destination "$auditHost/Binaries/Win64"
    }
    $moduleHash=(Get-FileHash -LiteralPath "$auditHost/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash
    $world="$auditProject/Saved/SaveGames/TemperateHills_World.sav"
    $worldHash=(Get-FileHash -LiteralPath $world).Hash
    Copy-Item -LiteralPath $world -Destination "$auditHost/Saved/SaveGames/TemperateHills_World.sav"
    @{module_sha256=$moduleHash;source_world_sha256=$worldHash;build=$Build;lag_ms=60;loss_percent=2;rendered=$false}|ConvertTo-Json|Set-Content -LiteralPath "$auditRun/inputs.json"
    $hostPeer=Start-AuditPeer 'host' '/Game/GameMaps/L_TemperateHills_Initial?listen?HillsContinue'
    Wait-AuditMarker "IpNetDriver listening on port $auditPort" $hostPeer
    $auditMutex.ReleaseMutex()
    $auditHeld=$false
    $guestPeer=Start-AuditPeer 'guest' ('127.0.0.1:'+$auditPort)
    Wait-AuditMarker 'VILLAGE_NET_DISCONNECT_CLIENT' $hostPeer -Guest $guestPeer
    Stop-AuditPeer $guestPeer
    @{pid=$guestPeer.Id;expected_forced_disconnect=$true;exit_code=$guestPeer.ExitCode}|ConvertTo-Json|Set-Content -LiteralPath "$auditRun/exit-guest.json"
    Wait-AuditMarker 'VILLAGE_NET_RECONNECT_READY' $hostPeer 180
    $rejoin=Start-AuditPeer 'guest' ('127.0.0.1:'+$auditPort) -Rejoin
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    while(-not(Test-Path -LiteralPath "$auditRun/Evidence/result.json")) {
        if($hostPeer.HasExited -or [DateTime]::UtcNow -gt $deadline){throw 'Missing final test receipt'}
        Start-Sleep -Seconds 2
    }
    $clean=$true
    foreach($pair in @(@('host',$hostPeer),@('rejoin',$rejoin))) {
        [void]$pair[1].WaitForExit(30000)
        $clean=$clean -and $pair[1].HasExited -and ($pair[1].ExitCode -eq 0)
        @{pid=$pair[1].Id;exited=$pair[1].HasExited;exit_code=$pair[1].ExitCode}|ConvertTo-Json|Set-Content -LiteralPath "$auditRun/exit-$($pair[0]).json"
    }
    $r=Get-Content -LiteralPath "$auditRun/Evidence/result.json" -Raw|ConvertFrom-Json
    $initial=if($Construction){@($r.checks | Where-Object {$_.case -eq 'same_guest_reconnects_with_upgrades_and_paid_bay' -and $_.passed}).Count -eq 1}
        else{Select-String -LiteralPath "$auditRun/rejoin.log" -Pattern 'VILLAGE_NET_GATE_INITIAL id=10000 angle=88.00 left=88.00 right=-88.00' -Quiet}
    $unchanged=(Get-FileHash -LiteralPath $world).Hash -eq $worldHash
    $passed=$r.passed -and $clean -and $initial -and $unchanged
    $summary=@{passed=$passed;cases=$r.checks.Count;clean_exit=$clean;source_world_unchanged=$unchanged;module_sha256=$moduleHash;real_udp=$true;rendered=$false}
    if($Construction){$summary.late_join_construction_state=$initial}else{$summary.late_join_initial_pose=$initial}
    $summary|ConvertTo-Json|Set-Content -LiteralPath "$auditRun/summary.json"
    Write-Output "VILLAGE_NET_DONE passed=$passed run=$auditRun"
    if(-not $passed){throw 'One or more network checks failed'}
} finally {
    foreach($peer in $auditOwned){Stop-AuditPeer $peer}
    if($auditHeld){$auditMutex.ReleaseMutex()}
    $auditMutex.Dispose()
}
