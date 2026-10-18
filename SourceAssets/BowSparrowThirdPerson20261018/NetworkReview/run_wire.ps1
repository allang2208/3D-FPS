param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$sparrowWireRoot='D:/FPS3D/FPSGAME'
$sparrowWireStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$sparrowWireDir=Join-Path $PSScriptRoot ('Wire/'+$sparrowWireStamp)
New-Item -ItemType Directory -Force -Path $sparrowWireDir | Out-Null
$sparrowWirePort=19879
if(Get-NetUDPEndpoint -LocalPort $sparrowWirePort -ErrorAction SilentlyContinue){throw 'Sparrow presentation audit port occupied.'}
$sparrowWireGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$sparrowWireHeld=$false
$sparrowWireOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$sparrowWireSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Start-SparrowPeer([string]$role,[string]$map){
    $peerArgs=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-ShotgunWireAudit','-BowSparrowWire','-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=ShotgunWireAudit_'+$sparrowWireStamp+'_'+$role),('-port='+$sparrowWirePort),
        ('-UserDir="'+$sparrowWireDir+'/'+$role+'/"'),('-ShotgunWireOutput="'+(Join-Path $sparrowWireDir ($role+'.json'))+'"'),
        ('-abslog="'+(Join-Path $sparrowWireDir ($role+'.log'))+'"'),'-ExecCmds="t.MaxFPS 30"')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $sparrowWireOwned.Add($peer);Write-Output "Sparrow_WIRE_PEER $role PID=$($peer.Id)";return $peer
}
function Wait-SparrowMarker([string]$marker,[System.Diagnostics.Process]$server){
    $deadline=(Get-Date).AddMinutes(4)
    while((Get-Date) -lt $deadline){
        if((Test-Path -LiteralPath "$sparrowWireDir/host.log") -and (Select-String -LiteralPath "$sparrowWireDir/host.log" -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker"}
        Start-Sleep -Seconds 1
    }
    throw "Audit timeout waiting for $marker"
}
try{
    Write-Output 'Waiting for the shared UE batch.'
    try{$sparrowWireHeld=$sparrowWireGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$sparrowWireHeld=$true}
    if(-not $sparrowWireHeld){throw 'Existing UE batch remained busy.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    if(-not $SkipBuild){
        $deadline=(Get-Date).AddMinutes(10)
        do{
            $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor-Cmd.exe','dotnet.exe','UnrealBuildTool.exe')) -and $_.CommandLine -like '*FPSGAME*'})
            if($busy.Count){if((Get-Date) -gt $deadline){throw 'Existing project build remained active.'};Start-Sleep -Seconds 5}
        }while($busy.Count)
        & "$sparrowWireRoot/Tools/Build/Build-Editor.ps1" *> (Join-Path $sparrowWireDir 'build-editor.log')
        Get-Content -LiteralPath (Join-Path $sparrowWireDir 'build-editor.log') -Tail 7
    }
    $hostOutput=Start-SparrowPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ShotgunWireAuditGameMode?listen';$hostPeer=$hostOutput[-1]
    $hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SparrowMarker 'SHOTGUN_WIRE_HOST_READY' $hostPeer
    $clientOutput=Start-SparrowPeer 'client' ('127.0.0.1:'+$sparrowWirePort);$clientPeer=$clientOutput[-1]
    $clientOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SparrowMarker 'SPARROW_PRESENTATION_REJOIN_READY' $hostPeer
    if(-not $clientPeer.WaitForExit(30000)){throw 'First audit client did not finish exiting.'}
    $rejoinOutput=Start-SparrowPeer 'rejoin' ('127.0.0.1:'+$sparrowWirePort)
    $rejoinOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SparrowMarker 'SHOTGUN_WIRE_RESULT' $hostPeer
    $peerExits=@()
    foreach($peer in $sparrowWireOwned){
        if(-not $peer.WaitForExit(30000)){throw "Audit peer PID=$($peer.Id) did not exit normally after its final result."}
        $peerExits+=@{pid=$peer.Id;exit_code=$peer.ExitCode}
    }
    $result=Get-Content -LiteralPath "$sparrowWireDir/host.json" -Raw | ConvertFrom-Json
    $complete=$result.passed -and -not @($peerExits | Where-Object { $_.exit_code -ne 0 }).Count
    @{directory=$sparrowWireDir;passed=$complete;peer_exits=$peerExits;transport='real local UDP listen host + client + fresh reconnect';port=$sparrowWirePort;lag_ms_each_peer=60;loss_percent_each_peer=5;rendered=$false} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'wire-receipt.json') -Encoding utf8
    Write-Output "Sparrow_WIRE_FINISHED PASS=$complete PATH=$sparrowWireDir"
    if(-not $complete){exit 1}
}finally{
    foreach($peer in $sparrowWireOwned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-BowSparrowWire*' -and $live.CommandLine -like ('*'+$sparrowWireStamp+'*')){Stop-Process -Id $peer.Id}
        }
    }
    $env:UE_SKIP_UBT_SDK_SETUP=$sparrowWireSdk
    if($sparrowWireHeld){$sparrowWireGate.ReleaseMutex()};$sparrowWireGate.Dispose()
}
