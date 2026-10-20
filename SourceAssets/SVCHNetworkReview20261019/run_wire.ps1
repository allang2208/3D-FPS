param([switch]$SkipBuild,[switch]$SkipPresentation=$true)
$ErrorActionPreference='Stop'
$s12WireRoot='D:/FPS3D/FPSGAME'
$s12WireOutputRoot=Join-Path $s12WireRoot 'SourceAssets/SVCHNetworkReview20261019/Receipts'
$s12WireStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$s12WireDir=Join-Path $s12WireOutputRoot ('Wire/'+$s12WireStamp)
New-Item -ItemType Directory -Force -Path $s12WireDir | Out-Null
$s12WirePort=19883
if(Get-NetUDPEndpoint -LocalPort $s12WirePort -ErrorAction SilentlyContinue){throw 'SVCH presentation audit port occupied.'}
$s12WireGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$s12WireHeld=$false
$s12WireOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$s12WireSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Start-SVCHPeer([string]$role,[string]$map){
    $peerArgs=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-ShotgunWireAudit','-SVCH','-M870PresentationWire','-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=ShotgunWireAudit_SVCH_'+$s12WireStamp+'_'+$role),('-port='+$s12WirePort),
        ('-UserDir="'+$s12WireDir+'/'+$role+'/"'),('-ShotgunWireOutput="'+(Join-Path $s12WireDir ($role+'.json'))+'"'),
        ('-abslog="'+(Join-Path $s12WireDir ($role+'.log'))+'"'),'-ExecCmds="fps.body.AsyncPreload 0,t.MaxFPS 30"')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $s12WireOwned.Add($peer);Write-Output "SVCH_WIRE_PEER $role PID=$($peer.Id)";return $peer
}
function Wait-SVCHMarker([string]$marker,[System.Diagnostics.Process]$server){
    $deadline=(Get-Date).AddMinutes(4)
    while((Get-Date) -lt $deadline){
        if((Test-Path -LiteralPath "$s12WireDir/host.log") -and (Select-String -LiteralPath "$s12WireDir/host.log" -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker"}
        Start-Sleep -Seconds 1
    }
    throw "Audit timeout waiting for $marker"
}
try{
    Write-Output 'Waiting for the shared UE batch.'
    try{$s12WireHeld=$s12WireGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$s12WireHeld=$true}
    if(-not $s12WireHeld){throw 'Existing UE batch remained busy.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Interactive editor opened; preserve it.'}
    if(-not $SkipBuild){
        $deadline=(Get-Date).AddMinutes(10)
        do{
            $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor-Cmd.exe','dotnet.exe','UnrealBuildTool.exe')) -and $_.CommandLine -like '*FPSGAME*'})
            if($busy.Count){if((Get-Date) -gt $deadline){throw 'Existing project build remained active.'};Start-Sleep -Seconds 5}
        }while($busy.Count)
        & "$s12WireRoot/Tools/Build/Build-Editor.ps1" *> (Join-Path $s12WireDir 'build-editor.log')
        Get-Content -LiteralPath (Join-Path $s12WireDir 'build-editor.log') -Tail 7
    }
    if(-not $SkipPresentation){
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$s12WireRoot/FPSGAME.uproject" -run=ShotgunAttachmentAudit -Saiga12KPresentation -nullrhi -nosound -unattended -nop4 -nosplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$s12WireDir/presentation.log" *> "$s12WireDir/presentation-console.log"
    $s12PresentationExit=$LASTEXITCODE
    Copy-Item -LiteralPath "$s12WireRoot/Saved/Saiga12KThirdPerson20261018/result.json" -Destination "$s12WireDir/presentation.json"
    if($s12PresentationExit -ne 0){throw "SVCH presentation regression failed: $s12PresentationExit"}
    }
    $s12Inputs=@('Source/FPSGAME/Weapons/SVCHForegripAssets.h','Source/FPSGAME/Weapons/SVCHMagazineAssets.h','Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp','Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp','Source/FPSGAME/Weapons/M870PresentationWireAudit.cpp','Binaries/Win64/UnrealEditor-FPSGAME.dll','Content/Weapons/SVDDragunov20260922/Accessories20260923/Meshes/SM_SVD_angled.uasset','Content/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_angled.uasset')
    $s12Inputs | ForEach-Object {Get-FileHash -LiteralPath (Join-Path $s12WireRoot $_)} | Select-Object Path,Hash | ConvertTo-Json | Set-Content -LiteralPath "$s12WireDir/input-hashes.json" -Encoding utf8
    $hostOutput=Start-SVCHPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ShotgunWireAuditGameMode?listen';$hostPeer=$hostOutput[-1]
    $hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SVCHMarker 'SHOTGUN_WIRE_HOST_READY' $hostPeer
    $clientOutput=Start-SVCHPeer 'client' ('127.0.0.1:'+$s12WirePort);$clientPeer=$clientOutput[-1]
    $clientOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SVCHMarker 'M870_PRESENTATION_REJOIN_READY' $hostPeer
    if(-not $clientPeer.WaitForExit(30000)){throw 'First audit client did not finish exiting.'}
    $rejoinOutput=Start-SVCHPeer 'rejoin' ('127.0.0.1:'+$s12WirePort)
    $rejoinOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SVCHMarker 'SHOTGUN_WIRE_RESULT' $hostPeer
    $result=Get-Content -LiteralPath "$s12WireDir/host.json" -Raw | ConvertFrom-Json
    @{directory=$s12WireDir;passed=$result.passed;transport='real local UDP listen host + client + fresh reconnect';port=$s12WirePort;lag_ms_each_peer=60;loss_percent_each_peer=5;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $s12WireOutputRoot 'wire-receipt.json') -Encoding utf8
    Write-Output "SVCH_WIRE_FINISHED PASS=$($result.passed) PATH=$s12WireDir"
    if(-not $result.passed){exit 1}
}finally{
    foreach($peer in $s12WireOwned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-M870PresentationWire*' -and $live.CommandLine -like ('*'+$s12WireStamp+'*')){Stop-Process -Id $peer.Id}
        }
    }
    $env:UE_SKIP_UBT_SDK_SETUP=$s12WireSdk
    if($s12WireHeld){$s12WireGate.ReleaseMutex()};$s12WireGate.Dispose()
}
