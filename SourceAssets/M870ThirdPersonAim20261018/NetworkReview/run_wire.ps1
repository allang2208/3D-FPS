param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$m870WireRoot='D:/FPS3D/FPSGAME'
$m870WireStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$m870WireDir=Join-Path $PSScriptRoot ('Wire/'+$m870WireStamp)
New-Item -ItemType Directory -Force -Path $m870WireDir | Out-Null
$m870WirePort=19878
if(Get-NetUDPEndpoint -LocalPort $m870WirePort -ErrorAction SilentlyContinue){throw 'M870 presentation audit port occupied.'}
$m870WireGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m870WireHeld=$false
$m870WireOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$m870WireSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Start-M870Peer([string]$role,[string]$map){
    $peerArgs=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-ShotgunWireAudit','-M870','-M870PresentationWire','-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=ShotgunWireAudit_'+$m870WireStamp+'_'+$role),('-port='+$m870WirePort),
        ('-UserDir="'+$m870WireDir+'/'+$role+'/"'),('-ShotgunWireOutput="'+(Join-Path $m870WireDir ($role+'.json'))+'"'),
        ('-abslog="'+(Join-Path $m870WireDir ($role+'.log'))+'"'),'-ExecCmds="t.MaxFPS 30"')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $m870WireOwned.Add($peer);Write-Output "M870_WIRE_PEER $role PID=$($peer.Id)";return $peer
}
function Wait-M870Marker([string]$marker,[System.Diagnostics.Process]$server){
    $deadline=(Get-Date).AddMinutes(4)
    while((Get-Date) -lt $deadline){
        if((Test-Path -LiteralPath "$m870WireDir/host.log") -and (Select-String -LiteralPath "$m870WireDir/host.log" -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker"}
        Start-Sleep -Seconds 1
    }
    throw "Audit timeout waiting for $marker"
}
try{
    Write-Output 'Waiting for the shared UE batch.'
    try{$m870WireHeld=$m870WireGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m870WireHeld=$true}
    if(-not $m870WireHeld){throw 'Existing UE batch remained busy.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    if(-not $SkipBuild){
        $deadline=(Get-Date).AddMinutes(10)
        do{
            $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor-Cmd.exe','dotnet.exe','UnrealBuildTool.exe')) -and $_.CommandLine -like '*FPSGAME*'})
            if($busy.Count){if((Get-Date) -gt $deadline){throw 'Existing project build remained active.'};Start-Sleep -Seconds 5}
        }while($busy.Count)
        & "$m870WireRoot/Tools/Build/Build-Editor.ps1" *> (Join-Path $m870WireDir 'build-editor.log')
        Get-Content -LiteralPath (Join-Path $m870WireDir 'build-editor.log') -Tail 7
    }
    $hostOutput=Start-M870Peer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ShotgunWireAuditGameMode?listen';$hostPeer=$hostOutput[-1]
    $hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-M870Marker 'SHOTGUN_WIRE_HOST_READY' $hostPeer
    $clientOutput=Start-M870Peer 'client' ('127.0.0.1:'+$m870WirePort);$clientPeer=$clientOutput[-1]
    $clientOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-M870Marker 'M870_PRESENTATION_REJOIN_READY' $hostPeer
    if(-not $clientPeer.WaitForExit(30000)){throw 'First audit client did not finish exiting.'}
    $rejoinOutput=Start-M870Peer 'rejoin' ('127.0.0.1:'+$m870WirePort)
    $rejoinOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-M870Marker 'SHOTGUN_WIRE_RESULT' $hostPeer
    $result=Get-Content -LiteralPath "$m870WireDir/host.json" -Raw | ConvertFrom-Json
    @{directory=$m870WireDir;passed=$result.passed;transport='real local UDP listen host + client + fresh reconnect';port=$m870WirePort;lag_ms_each_peer=60;loss_percent_each_peer=5;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'wire-receipt.json') -Encoding utf8
    Write-Output "M870_WIRE_FINISHED PASS=$($result.passed) PATH=$m870WireDir"
    if(-not $result.passed){exit 1}
}finally{
    foreach($peer in $m870WireOwned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-M870PresentationWire*' -and $live.CommandLine -like ('*'+$m870WireStamp+'*')){Stop-Process -Id $peer.Id}
        }
    }
    $env:UE_SKIP_UBT_SDK_SETUP=$m870WireSdk
    if($m870WireHeld){$m870WireGate.ReleaseMutex()};$m870WireGate.Dispose()
}
