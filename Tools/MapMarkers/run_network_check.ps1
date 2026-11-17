param([string]$Run='normal-01',[int]$Lag=0,[int]$Loss=0,[int]$Port=19938)
$ErrorActionPreference='Stop'
$mmRoot='D:/FPS3D/FPSGAME'
$mmOut="$mmRoot/Saved/MapMarkerSharing20261115/$Run"
$mmRuntime="$mmOut/Runtime"
$mmExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$mmStamp=(Get-Date).ToString('yyyyMMddHHmmssfff')
$mmOwned=@();$mmLaunches=@();$mmGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$mmHeld=$false
if(Test-Path "$mmOut/result.json"){throw 'Use a new run name; preserving prior evidence'}
New-Item -ItemType Directory -Force -Path $mmOut | Out-Null
function Start-MarkerPeer([string]$Role,[string]$Map,[string]$Profile){
 $mmArgs=@("`"$mmRuntime/FPSGAME.uproject`"","`"$Map`"",'-game','-nullrhi','-RenderOffscreen','-nosound','-unattended','-nosplash','-MapMarkerWire','-SkipStartupMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
 '-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
 '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
 "-ColdSteelProfile=MapMarker_${mmStamp}_$Profile","-port=$Port","-PktLag=$Lag","-PktLoss=$Loss",
 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
 "-UserDir=`"$mmOut/$Profile/`"","-MapMarkerWireOutput=`"$mmOut/result.json`"","-abslog=`"$mmOut/$Role.log`"",
 '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh',
 '-DPCvars=fps.body.WorldBodySuppress=1','-ExecCmds="t.MaxFPS 30"')
 $mmPeer=Start-Process -FilePath $mmExe -ArgumentList $mmArgs -WorkingDirectory $mmRoot -WindowStyle Hidden -PassThru
 $null=$mmPeer.Handle
 $script:mmOwned+=$mmPeer
 $script:mmLaunches+=@{role=$Role;profile=$Profile;pid=$mmPeer.Id;exe=$mmExe;args=$mmArgs;started=(Get-Date).ToString('o')}
 $script:mmLaunches | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$mmOut/launches.json" -Encoding utf8
 return $mmPeer
}
function Wait-MarkerLog([string]$Marker,[Diagnostics.Process]$Peer){
 $mmDeadline=[DateTime]::UtcNow.AddMinutes(7)
 while([DateTime]::UtcNow -lt $mmDeadline){
  if(Test-Path "$mmOut/host.log"){
   if(Select-String -LiteralPath "$mmOut/host.log" -SimpleMatch $Marker -Quiet){return}
   if(Select-String -LiteralPath "$mmOut/host.log" -SimpleMatch 'MAP_MARKER_WIRE_RESULT pass=0' -Quiet){throw 'Feature test failed; see result.json'}
  }
  $Peer.Refresh();if($Peer.HasExited){throw "Host exited before $Marker"}
  Start-Sleep -Seconds 2
 }
 throw "Timed out waiting for $Marker"
}
try{
 Write-Output 'Waiting for shared UE test window.'
 try{$mmHeld=$mmGate.WaitOne(0)}catch [Threading.AbandonedMutexException]{$mmHeld=$true}
 while(-not $mmHeld){try{$mmHeld=$mmGate.WaitOne(50000)}catch [Threading.AbandonedMutexException]{$mmHeld=$true}}
 if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -like '*FPSGAME.uproject*'}){throw 'Preserving active editor'}
 while(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*'}){Start-Sleep -Seconds 5}
 if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 8MB){throw 'Less than 8 GB RAM free; defer two-process test'}
 if(Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue){throw 'Test port occupied; select another port'}
 New-Item -ItemType Directory -Force -Path "$mmRuntime/Binaries/Win64" | Out-Null
 Copy-Item -LiteralPath "$mmRoot/FPSGAME.uproject" -Destination "$mmRuntime/FPSGAME.uproject"
 foreach($mmDirectory in @('Content','Config')){
  New-Item -ItemType Junction -Path "$mmRuntime/$mmDirectory" -Target "$mmRoot/$mmDirectory" | Out-Null
 }
 Get-ChildItem -LiteralPath "$mmRoot/Binaries/Win64" -File | Where-Object {$_.Extension -in @('.dll','.modules','.target')} | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination "$mmRuntime/Binaries/Win64/$($_.Name)"}
 # Freeze native plugin libraries too; resource/source junctions are read-only inputs for these tests.
 $mmNative=@()
 foreach($mmPlugin in Get-ChildItem -LiteralPath "$mmRoot/Plugins" -Directory){
  $mmPluginCopy="$mmRuntime/Plugins/$($mmPlugin.Name)"
  New-Item -ItemType Directory -Force -Path $mmPluginCopy | Out-Null
  foreach($mmEntry in Get-ChildItem -LiteralPath $mmPlugin.FullName){
   if($mmEntry.PSIsContainer -and $mmEntry.Name -eq 'Binaries'){
    foreach($mmBinary in Get-ChildItem -LiteralPath $mmEntry.FullName -Recurse -File | Where-Object {$_.Extension -in @('.dll','.modules','.target')}){
     $mmRelative=[IO.Path]::GetRelativePath($mmPlugin.FullName,$mmBinary.FullName)
     $mmDestination=Join-Path $mmPluginCopy $mmRelative
     New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($mmDestination)) | Out-Null
     Copy-Item -LiteralPath $mmBinary.FullName -Destination $mmDestination
     $mmNative+=@{path="Plugins/$($mmPlugin.Name)/$mmRelative";sha256=(Get-FileHash -LiteralPath $mmDestination -Algorithm SHA256).Hash}
    }
   }elseif($mmEntry.PSIsContainer){New-Item -ItemType Junction -Path "$mmPluginCopy/$($mmEntry.Name)" -Target $mmEntry.FullName | Out-Null}
   else{Copy-Item -LiteralPath $mmEntry.FullName -Destination "$mmPluginCopy/$($mmEntry.Name)"}
  }
 }
 $mmVersion=@{dll=(Get-FileHash "$mmRuntime/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Algorithm SHA256).Hash;native_plugins=$mmNative;runtime=$mmRuntime;linked_read_only_inputs=@('Content','Config','plugin resources and sources');requested_lag_ms=$Lag;requested_loss_percent=$Loss;started=(Get-Date).ToString('o')}
 $mmVersion | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$mmOut/version.json" -Encoding utf8
 $mmHost=Start-MarkerPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ColdSteelMapMarkerWireGameMode?listen' 'host'
 Wait-MarkerLog 'MAP_MARKER_WIRE_HOST_READY' $mmHost
 $mmGuest=Start-MarkerPeer 'guest' "127.0.0.1:$Port" 'guest'
 Wait-MarkerLog 'MAP_MARKER_WIRE_REJOIN_READY' $mmHost
 if(-not $mmGuest.WaitForExit(15000)){throw 'First guest has not exited; preserving two-process limit'}
 if($mmGuest.ExitCode -ne 0){throw "First guest exit code $($mmGuest.ExitCode)"}
 $mmRejoin=Start-MarkerPeer 'rejoin' "127.0.0.1:$Port" 'guest'
 Wait-MarkerLog 'MAP_MARKER_WIRE_RESULT' $mmHost
 foreach($mmPeer in $mmOwned){if(-not $mmPeer.WaitForExit(20000)){throw "Test PID $($mmPeer.Id) did not exit"}}
 $mmResult=Get-Content -LiteralPath "$mmOut/result.json" -Raw | ConvertFrom-Json
 $mmExit=@($mmOwned | ForEach-Object {@{pid=$_.Id;exit_code=$_.ExitCode}})
 $mmOK=$mmResult.passed -and (@($mmExit | Where-Object {$_.exit_code -ne 0}).Count -eq 0)
 @{passed=$mmOK;transport='UDP listen host plus client, maximum two simultaneous processes';same_profile_reconnect=$true;requested_lag_ms=$Lag;requested_loss_percent=$Loss;exits=$mmExit;completed=(Get-Date).ToString('o')} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$mmOut/receipt.json" -Encoding utf8
 if(-not $mmOK){throw 'Network test failed; see result and exit codes'}
 Write-Output "Map marker UDP test passed: $mmOut"
}finally{
 foreach($mmPeer in $mmOwned){
  $mmPeer.Refresh();if(-not $mmPeer.HasExited){
   $mmCurrent=Get-CimInstance Win32_Process -Filter "ProcessId=$($mmPeer.Id)"
   if($mmCurrent.CommandLine -like '*-MapMarkerWire*' -and $mmCurrent.CommandLine -like "*$mmStamp*"){Stop-Process -Id $mmPeer.Id}
  }
 }
 if($mmHeld){$mmGate.ReleaseMutex()};$mmGate.Dispose()
}
