param([int]$Port=19998,[switch]$SkipBuild,[switch]$BaseOnly,[switch]$PrismOnly)
$ErrorActionPreference='Stop'
$reviewRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$reviewStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$reviewDir=Join-Path $reviewRoot ('SourceAssets/LMGStabilityGrip20261111/Review02/WireRuns/'+$reviewStamp)
New-Item -ItemType Directory -Path $reviewDir -Force | Out-Null
$reviewExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$reviewHeld=$false
$reviewOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-EquipPeer([string]$Role,[string]$Map){
    # Packet simulation uses wall time. Fixed simulation steps accelerate one
    # peer when its capture finishes first and invalidate the cosmetic lease.
    $peerArguments=@(('"'+(Join-Path $reviewRoot 'FPSGAME.uproject')+'"'),('"'+$Map+'"'),'-game','-RenderOffscreen','-ResX=1280','-ResY=720','-windowed','-nosound','-unattended','-nosplash','-NoLoadingScreen','-WeaponEquipWireAudit','-M249WristWire','-M249WristCapture','-LMGGripReview',
        '-DPCVars=fps.body.AsyncPreload=0,Editor.AsyncSkinnedAssetCompilation=0,Editor.AsyncStaticMeshCompilation=0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=EquipWireAudit_'+$reviewStamp+'_'+$Role),('-port='+$Port),
        ('-UserDir="'+$reviewDir+'/'+$Role+'/"'),('-EquipWireOutput="'+$reviewDir+'/'+$Role+'.json"'),
        ('-abslog="'+$reviewDir+'/'+$Role+'.log"'),'-ExecCmds="t.MaxFPS 15,r.MotionBlurQuality 0"')
    if($BaseOnly){$peerArguments+='-M249WristBaseOnly'}
    if($PrismOnly){$peerArguments+='-M249WristPrismOnly'}
    $peer=Start-Process -FilePath $reviewExe -ArgumentList $peerArguments -WindowStyle Hidden -PassThru
    $reviewOwned.Add($peer);Write-Output "EQUIP_WIRE_PEER $Role PID=$($peer.Id)";return $peer
}
function Wait-EquipMarker([string]$Marker,[System.Diagnostics.Process]$Peer){
    $deadline=(Get-Date).AddMinutes(30)
    while((Get-Date)-lt $deadline){
        if((Test-Path -LiteralPath "$reviewDir/host.log") -and (Select-String -LiteralPath "$reviewDir/host.log" -SimpleMatch $Marker -Quiet)){return}
        if($Peer.HasExited){throw "Host exited before $Marker"};Start-Sleep -Milliseconds 500
    }
    throw "Timeout waiting for $Marker"
}
try{
    try{$reviewHeld=$reviewGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$reviewHeld=$true}
    if(-not $reviewHeld){throw 'Existing UE batch remained busy.'}
    if(Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue){throw 'Review UDP port is occupied.'}
    $existing=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if($existing.Count){throw 'Existing UE process remains; no review peers started.'}
    if(-not $SkipBuild){
        & "$reviewRoot/Tools/Build/Build-Editor.ps1" *> "$PSScriptRoot/build.console.log"
        if(-not $? -or $LASTEXITCODE -ne 0){throw 'Visual capture build failed'}
    }
    $started=Start-EquipPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.WeaponEquipWireGameMode?listen'
    $hostPeer=$started[-1];$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-EquipMarker 'EQUIP_WIRE_HOST_READY' $hostPeer
    $started=Start-EquipPeer 'client' ('127.0.0.1:'+$Port)
    $clientPeer=$started[-1];$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-EquipMarker 'EQUIP_WIRE_RESULT' $hostPeer
    $exits=@();foreach($peer in $reviewOwned){if(-not $peer.WaitForExit(30000)){throw 'Review peer failed to exit after its result.'};$exits+=@{pid=$peer.Id;exit_code=$peer.ExitCode}}
    $hostResult=Get-Content -LiteralPath "$reviewDir/host.json" -Raw | ConvertFrom-Json
    $clientResult=Get-Content -LiteralPath "$reviewDir/client.json" -Raw | ConvertFrom-Json
    $ok=$hostResult.passed -and $clientResult.passed -and -not @($exits | Where-Object {$_.exit_code -ne 0}).Count
    @{passed=$ok;directory=$reviewDir;host_cases=$hostResult.cases.Count;client_cases=$clientResult.cases.Count;peer_exits=$exits;lag_ms_each_peer=80;loss_percent_each_peer=2;rendered=$true;clock='real delta; 15 FPS cap; no fixed timestep';profile_transport='production upload and mirror enabled'} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$reviewDir/receipt.json" -Encoding utf8
    Write-Output "EQUIP_WIRE_FINISHED passed=$ok directory=$reviewDir"
    if(-not $ok){exit 1}
}finally{
    foreach($peer in $reviewOwned){
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-WeaponEquipWireAudit*' -and $live.CommandLine -like ('*'+$reviewStamp+'*')){Stop-Process -Id $peer.Id}
        }
    }
    if($reviewHeld){$reviewGate.ReleaseMutex()};$reviewGate.Dispose()
}
