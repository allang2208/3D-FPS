param([string]$Run='wire-01')
$ErrorActionPreference='Stop'
$apRoot='D:/FPS3D/FPSGAME';$apOut="$apRoot/SourceAssets/FurnitureRest20261022/CompletionAudit20261025/$Run"
$apStamp=(Get-Date).ToString('yyyyMMddHHmmss');$apOwned=@();$apPort=19924
New-Item -ItemType Directory -Force -Path $apOut | Out-Null
$apGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$apHeld=$false
function Start-ApartmentPeer([string]$Role,[string]$Map){
 $apArgs=@("`"$apRoot/FPSGAME.uproject`"","`"$Map`"",'-game','-nullrhi','-RenderOffscreen','-nosound','-unattended','-nosplash','-ApartmentNetworkAudit',
 '-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0','-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
 "-ColdSteelProfile=ApartmentAudit_${apStamp}_$Role","-port=$apPort",'-PktLag=60','-PktLoss=5',"-UserDir=`"$apOut/$Role/`"","-ApartmentAuditOutput=`"$apOut/result.json`"","-abslog=`"$apOut/$Role.log`"",
 '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh',
 '-DPCvars=fps.body.WorldBodySuppress=1','-ExecCmds="t.MaxFPS 30"')
 $apPeer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $apArgs -WorkingDirectory $apRoot -WindowStyle Hidden -PassThru
 $script:apOwned+=$apPeer
 return $apPeer
}
function Wait-ApartmentMarker([string]$Marker,[Diagnostics.Process]$Peer){
 $apDeadline=[DateTime]::UtcNow.AddMinutes(5)
 while([DateTime]::UtcNow -lt $apDeadline){
  if((Test-Path "$apOut/host.log") -and (Select-String -LiteralPath "$apOut/host.log" -Pattern $Marker -Quiet)){return}
  $Peer.Refresh();if($Peer.HasExited){throw "Host exited before $Marker"}
  Start-Sleep -Seconds 2
 }
 throw "Timed out waiting for $Marker"
}
try{
 Write-Output 'Waiting once for shared UE network audit window.'
 try{$apHeld=$apGate.WaitOne([TimeSpan]::FromHours(2))}catch [Threading.AbandonedMutexException]{$apHeld=$true}
 if(-not $apHeld){throw 'Shared UE window remained busy'}
 if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -like '*FPSGAME.uproject*'}){throw 'Preserving active project editor'}
 if(Get-NetUDPEndpoint -LocalPort $apPort -ErrorAction SilentlyContinue){throw 'Audit port already in use'}
 $apHost=Start-ApartmentPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ApartmentNetworkAuditGameMode?listen'
 Wait-ApartmentMarker 'APARTMENT_NET_HOST_READY' $apHost
 $apGuest=Start-ApartmentPeer 'guest' "127.0.0.1:$apPort"
 Wait-ApartmentMarker 'APARTMENT_NET_LATE_JOIN_READY' $apHost
 $apLate=Start-ApartmentPeer 'late' "127.0.0.1:$apPort"
 Wait-ApartmentMarker 'APARTMENT_NET_RESULT' $apHost
 $apResult=Get-Content -LiteralPath "$apOut/result.json" -Raw | ConvertFrom-Json
 @{passed=$apResult.passed;transport='three isolated local UDP processes';requested_packet_lag_ms=60;requested_packet_loss_percent=5;interactive_editor_started=$false;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$apOut/receipt.json" -Encoding utf8
 if(-not $apResult.passed){throw 'Network audit reported a failure; see result.json'}
 Write-Output 'Apartment UDP audit completed.'
}finally{
 foreach($apPeer in $apOwned){
  $apPeer.Refresh();if(-not $apPeer.HasExited){[void]$apPeer.WaitForExit(5000)}
  $apPeer.Refresh();if(-not $apPeer.HasExited){
   $apCurrent=Get-CimInstance Win32_Process -Filter "ProcessId=$($apPeer.Id)"
   if($apCurrent.CommandLine -like '*-ApartmentNetworkAudit*' -and $apCurrent.CommandLine -like "*$apStamp*"){Stop-Process -Id $apPeer.Id}
  }
 }
 if($apHeld){$apGate.ReleaseMutex()};$apGate.Dispose()
}
