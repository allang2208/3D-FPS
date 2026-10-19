param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$mageProject='D:/FPS3D/FPSGAME';$mageStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$mageOut=Join-Path $mageProject ('SourceAssets/BlueMageSetAudit20261019/Wire/'+$mageStamp)
[void](New-Item -ItemType Directory -Force -Path $mageOut)
$magePort=19943;$mageGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$mageHeld=$false
$mageOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-MagePeer([string]$Role,[string]$Map){
    $profileRole=if($Role -eq 'host'){'host'}else{'client'}
    $arguments=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"',('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-MageOutfitWireAudit',
      '-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0','-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
      ('-ColdSteelProfile=MageAudit_'+$mageStamp+'_'+$profileRole),('-port='+$magePort),('-UserDir="'+$mageOut+'/'+$profileRole+'/"'),
      ('-MageOutfitWireOutput="'+$mageOut+'/'+$Role+'.json"'),('-abslog="'+$mageOut+'/'+$Role+'.log"'),
      '-ExecCmds="fps.body.AsyncPreload 0,t.MaxFPS 30,NetEmulation.PktLag 60,NetEmulation.PktLoss 3"')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $mageOwned.Add($peer);Write-Output "MAGE_WIRE_PEER $Role PID=$($peer.Id)";return $peer
}
function Wait-MageMarker([string]$Marker,[System.Diagnostics.Process]$HostPeer,[int]$Minutes=8){
    $until=(Get-Date).AddMinutes($Minutes)
    while((Get-Date)-lt $until){
        if((Test-Path -LiteralPath "$mageOut/host.log") -and (Select-String -LiteralPath "$mageOut/host.log" -SimpleMatch $Marker -Quiet)){return}
        if($HostPeer.HasExited){throw "Host exited before $Marker"};Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for $Marker"
}
try{
    Write-Output 'Queued for the shared UE audit batch.'
    try{$mageHeld=$mageGate.WaitOne()}catch [Threading.AbandonedMutexException]{$mageHeld=$true}
    while($true){
        $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','cl.exe','link.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(@($busy | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Interactive editor is open; preserve it.'}
        if(-not $busy.Count){break};Write-Output 'Waiting for active UE/build process.'
        try{Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    if(-not $SkipBuild){
        & "$mageProject/Tools/Build/Build-Editor.ps1" *> "$mageOut/build-editor.log"
        Get-Content -LiteralPath "$mageOut/build-editor.log" -Tail 7
    }
    $free=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
    if($free -lt 12){throw "Need memory for two isolated peers; only $([math]::Round($free,1)) GiB available."}
    if(Get-NetUDPEndpoint -LocalPort $magePort -ErrorAction SilentlyContinue){throw 'Audit port occupied.'}
    @('Binaries/Win64/UnrealEditor-FPSGAME.dll','Content/ColdSteelData/items.json','Content/ColdSteelData/modular_outfits.json','Content/ColdSteelData/player_body.json','Source/FPSGAME/Development/MageOutfitWireAudit.cpp') | ForEach-Object {Get-FileHash -LiteralPath (Join-Path $mageProject $_)} | Select-Object Path,Hash | ConvertTo-Json | Set-Content -LiteralPath "$mageOut/input-hashes.json" -Encoding utf8
    $started=Start-MagePeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.MageOutfitWireAuditGameMode?listen';$mageHost=$started[-1];$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-MageMarker 'MAGE_WIRE_HOST_READY' $mageHost 4
    $started=Start-MagePeer 'client' ('127.0.0.1:'+$magePort);$mageClient=$started[-1];$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-MageMarker 'MAGE_WIRE_REJOIN_READY' $mageHost
    if(-not $mageClient.WaitForExit(30000)){throw 'Initial client did not finish exiting.'}
    $started=Start-MagePeer 'rejoin' ('127.0.0.1:'+$magePort);$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-MageMarker 'MAGE_WIRE_RESULT' $mageHost
    $result=Get-Content -LiteralPath "$mageOut/host.json" -Raw | ConvertFrom-Json
    @{directory=$mageOut;passed=$result.passed;transport='UDP listen host + client + same-profile reconnect';port=$magePort;lag_ms_each_peer=60;loss_percent_each_peer=3;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$mageProject/SourceAssets/BlueMageSetAudit20261019/wire-receipt.json" -Encoding utf8
    Write-Output "MAGE_WIRE_FINISHED PASS=$($result.passed) PATH=$mageOut"
    if(-not $result.passed){exit 1}
}finally{
    foreach($peer in $mageOwned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)";if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-MageOutfitWireAudit*' -and $live.CommandLine -like ('*'+$mageStamp+'*')){Stop-Process -Id $peer.Id}}
    }
    if($mageHeld){$mageGate.ReleaseMutex()};$mageGate.Dispose()
}
