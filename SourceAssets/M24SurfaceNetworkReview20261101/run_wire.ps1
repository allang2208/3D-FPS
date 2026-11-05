param([switch]$SkipBuild,[string]$OutputRoot)
$ErrorActionPreference='Stop'
$m24WireRoot='D:/FPS3D/FPSGAME'
$m24WireOutputRoot=Join-Path $m24WireRoot 'SourceAssets/M24SurfaceNetworkReview20261101/Receipts'
if($OutputRoot){$m24WireOutputRoot=[IO.Path]::GetFullPath($OutputRoot)}
$m24WireStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$m24WireDir=Join-Path $m24WireOutputRoot ('Wire/'+$m24WireStamp)
New-Item -ItemType Directory -Force -Path $m24WireDir | Out-Null
$m24WirePort=19881
if(Get-NetUDPEndpoint -LocalPort $m24WirePort -ErrorAction SilentlyContinue){throw 'M24 presentation audit port occupied.'}
$m24WireGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m24WireHeld=$false
$m24WireOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$m24WireSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Start-M24Peer([string]$role,[string]$map){
    $peerArgs=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-ShotgunWireAudit','-M24','-M870PresentationWire','-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=ShotgunWireAudit_M24_'+$m24WireStamp+'_'+$role),('-port='+$m24WirePort),
        ('-UserDir="'+$m24WireDir+'/'+$role+'/"'),('-ShotgunWireOutput="'+(Join-Path $m24WireDir ($role+'.json'))+'"'),
        ('-abslog="'+(Join-Path $m24WireDir ($role+'.log'))+'"'),'-ExecCmds="fps.body.AsyncPreload 0,t.MaxFPS 30"')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $m24WireOwned.Add($peer);Write-Output "M24_WIRE_PEER $role PID=$($peer.Id)";return $peer
}
function Wait-M24Marker([string]$marker,[System.Diagnostics.Process]$server){
    $deadline=(Get-Date).AddMinutes(4)
    while((Get-Date) -lt $deadline){
        if((Test-Path -LiteralPath "$m24WireDir/host.log") -and (Select-String -LiteralPath "$m24WireDir/host.log" -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker"}
        Start-Sleep -Seconds 1
    }
    throw "Audit timeout waiting for $marker"
}
try{
    Write-Output 'Waiting for the shared UE batch.'
    try{$m24WireHeld=$m24WireGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m24WireHeld=$true}
    if(-not $m24WireHeld){throw 'Existing UE batch remained busy.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Interactive editor opened; preserve it.'}
    if(-not $SkipBuild){
        $deadline=(Get-Date).AddMinutes(10)
        do{
            $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor-Cmd.exe','dotnet.exe','UnrealBuildTool.exe')) -and $_.CommandLine -like '*FPSGAME*'})
            if($busy.Count){if((Get-Date) -gt $deadline){throw 'Existing project build remained active.'};Start-Sleep -Seconds 5}
        }while($busy.Count)
        & "$m24WireRoot/Tools/Build/Build-Editor.ps1" *> (Join-Path $m24WireDir 'build-editor.log')
        Get-Content -LiteralPath (Join-Path $m24WireDir 'build-editor.log') -Tail 7
    }
    $m24Inputs=@('Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp','Source/FPSGAME/Characters/FPSBodyRifleHold.cpp','Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp','Source/FPSGAME/Weapons/M870PresentationWireAudit.cpp','Config/DefaultGame.ini','Binaries/Win64/UnrealEditor-FPSGAME.dll','Content/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_AdvancedFront_ForIndependentGrip.uasset','Content/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_ReceiverStock_Advanced.uasset')
    $m24Inputs | ForEach-Object {Get-FileHash -LiteralPath (Join-Path $m24WireRoot $_)} | Select-Object Path,Hash | ConvertTo-Json | Set-Content -LiteralPath "$m24WireDir/input-hashes.json" -Encoding utf8
    $hostOutput=Start-M24Peer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ShotgunWireAuditGameMode?listen';$hostPeer=$hostOutput[-1]
    $hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-M24Marker 'SHOTGUN_WIRE_HOST_READY' $hostPeer
    $clientOutput=Start-M24Peer 'client' ('127.0.0.1:'+$m24WirePort);$clientPeer=$clientOutput[-1]
    $clientOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-M24Marker 'M870_PRESENTATION_REJOIN_READY' $hostPeer
    if(-not $clientPeer.WaitForExit(30000)){throw 'First audit client did not finish exiting.'}
    $rejoinOutput=Start-M24Peer 'rejoin' ('127.0.0.1:'+$m24WirePort)
    $rejoinOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-M24Marker 'SHOTGUN_WIRE_RESULT' $hostPeer
    $result=Get-Content -LiteralPath "$m24WireDir/host.json" -Raw | ConvertFrom-Json
    @{directory=$m24WireDir;passed=$result.passed;transport='real local UDP listen host + client + fresh reconnect';port=$m24WirePort;lag_ms_each_peer=60;loss_percent_each_peer=5;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $m24WireOutputRoot 'wire-receipt.json') -Encoding utf8
    Write-Output "M24_WIRE_FINISHED PASS=$($result.passed) PATH=$m24WireDir"
    if(-not $result.passed){exit 1}
}finally{
    foreach($peer in $m24WireOwned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-M870PresentationWire*' -and $live.CommandLine -like ('*'+$m24WireStamp+'*')){Stop-Process -Id $peer.Id}
        }
    }
    $env:UE_SKIP_UBT_SDK_SETUP=$m24WireSdk
    if($m24WireHeld){$m24WireGate.ReleaseMutex()};$m24WireGate.Dispose()
}
