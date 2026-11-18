param([string]$Attempt='fixed01',[switch]$SkipBuild,[switch]$RenderClients,[Alias('TraceClients')][switch]$TraceRuntime,[string]$ModuleDirectory='',[string]$SaveDirectory='',[ValidateRange(1,16)][int]$MaxParallelActions=2)
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME';$run="$project/Saved/HillsNetLoad20261118/$Attempt"
$private="$run/Host";$port=20329
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[Collections.Generic.List[Diagnostics.Process]]::new()
$script:CleanExits=$true
function Launch([string]$Role){
 $dir="$run/Users/$Role";New-Item -ItemType Directory -Force -Path $dir|Out-Null
 $map=if($Role -eq 'host'){'/Game/GameMaps/L_TemperateHills_Initial?listen?HillsContinue'}else{'127.0.0.1:'+$port}
 $arguments=@(('"'+$private+'/FPSGAME.uproject"'),('"'+$map+'"'),'-game','-nosound','-unattended','-nosplash',
 '-HillsNetLoadAudit',('-HillsNetLoadRole='+$Role),'-HillsContinue','-SkipStartupMenu','-ClearwaterNoMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',('-port='+$port),
 ('-ColdSteelProfile=HillsNetLoad_'+$Attempt+'_'+$Role),('-UserDir="'+$dir+'"'),('-abslog="'+$run+'/'+$Role+'.log"'),
 ('-HillsNetLoadOutput="'+$run+'/Evidence"'),'-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
 '-ExecCmds="t.MaxFPS 45,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,net.ReportSyncLoads 1,net.PackageMap.LongLoadThreshhold 0.001"',
 '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
 '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
 '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
 '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False')
 if($RenderClients -and $Role -ne 'host'){$arguments+=@('-d3d12','-RenderOffscreen','-ResX=1280','-ResY=720','-ForceRes','-windowed')}else{$arguments+='-nullrhi'}
 if($TraceRuntime){$arguments+=@('-trace=cpu,frame,loadtime','-statnamedevents',('-tracefile="'+$run+'/'+$Role+'.utrace"'))}
 $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
 $handle=$p.Handle;$owned.Add($p)
 @{pid=$p.Id;args=$arguments;role=$Role}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$run/launch-$Role.json"
 Write-Host "HILLS_NETLOAD_STARTED $Role pid=$($p.Id)";return $p
}
function WaitMarker([string]$Path,[string]$Text,[Diagnostics.Process]$Peer,[int]$Seconds=950){
 $end=[DateTime]::UtcNow.AddSeconds($Seconds)
 while([DateTime]::UtcNow -lt $end){
  if((Test-Path -LiteralPath $Path) -and (($Text -eq '') -or (Select-String -LiteralPath $Path -SimpleMatch $Text -Quiet))){return}
  if($Peer.HasExited){throw "Process exited before $Path $Text"};Start-Sleep -Seconds 2
 };throw "Timeout waiting for $Path $Text"
}
function ExitReceipt([string]$Role,[Diagnostics.Process]$Peer){
 [void]$Peer.WaitForExit(30000);$code=if($Peer.HasExited){$Peer.ExitCode}else{$null}
 @{pid=$Peer.Id;exited=$Peer.HasExited;exit_code=$code}|ConvertTo-Json|Set-Content -LiteralPath "$run/exit-$Role.json"
 if(-not $Peer.HasExited){throw "$Role did not finish exiting"}
 if($code -ne 0){$script:CleanExits=$false;Write-Output "HILLS_NETLOAD_EXIT_FAILURE $Role code=$code; preserving the failure while continuing remaining checks."}
}
try{
 Write-Output 'Waiting for the existing UE batch gate.'
 try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
 if(Test-Path -LiteralPath $run){throw 'Attempt already exists; retain its evidence and use another name.'}
 New-Item -ItemType Directory -Force -Path "$run/Build","$run/Evidence"|Out-Null
 # Publish the new uncooked-runtime module under the UE batch gate, immediately
 # before building it. Parallel private editor hosts must not discover an enabled
 # plugin while its first binary is still absent.
 $runtimePlugin="$project/Plugins/FPSStandaloneRuntime/FPSStandaloneRuntime.uplugin"
 if(-not $SkipBuild -and (Test-Path -LiteralPath $runtimePlugin)){
  $descriptor=Get-Content -LiteralPath $runtimePlugin -Raw|ConvertFrom-Json
  if(-not $descriptor.EnabledByDefault){
   $descriptor.EnabledByDefault=$true
   [IO.File]::WriteAllText($runtimePlugin,($descriptor|ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
  }
 }
 if(-not $SkipBuild){& "$project/Tools/WorldGeneration/Build-VillageDefenses.ps1" -OutputRoot "$run/Build" -MaxParallelActions $MaxParallelActions}
 if(-not $SkipBuild){foreach($target in 'FPSGAMEEditor','FPSGAME'){
  if((Get-Content -LiteralPath "$run/Build/$target-build.json" -Raw|ConvertFrom-Json).exit_code -ne 0){throw "$target build failed"}
 }}
 $busy=Get-CimInstance Win32_Process|Where-Object {$_.Name -in 'UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe'}
 if($busy){throw 'An engine process remains active; preserve it.'}
 if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Port occupied'}
 New-Item -ItemType Directory -Force -Path "$private/Binaries/Win64","$run/Users/host/Saved/SaveGames","$run/OriginalSaveBackup"|Out-Null
 Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$private/FPSGAME.uproject"
 Copy-Item -LiteralPath "$project/Config" -Destination "$private/Config" -Recurse
 $settings=@{Enabled='True';MaxAlive='3';MaxPerNight='3';WaveSize='3'};$inRaid=$false
 $config=foreach($line in Get-Content -LiteralPath "$private/Config/DefaultGame.ini"){
  if($line -match '^\[([^\]]+)\]'){$inRaid=$Matches[1] -eq 'TemperateHills.NightRaid'}
  if($inRaid -and $line -match '^([^=]+)='){$key=$Matches[1];if($settings.ContainsKey($key)){"$key=$($settings[$key])";continue}};$line
 }
 [IO.File]::WriteAllLines("$private/Config/DefaultGame.ini",[string[]]$config,[Text.UTF8Encoding]::new($false))
 foreach($folder in 'Content','Plugins','Shaders'){New-Item -ItemType Junction -Path "$private/$folder" -Target "$project/$folder"|Out-Null}
 $moduleSource=if($ModuleDirectory){$ModuleDirectory}else{"$project/Binaries/Win64"}
 foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$moduleSource/$file" -Destination "$private/Binaries/Win64/$file"}
 $sources=@(Get-Item -LiteralPath "$project/Saved/SaveGames/TemperateHills_World.sav")+@(Get-ChildItem -LiteralPath "$project/Saved/SaveGames" -Filter 'HillsNight_*.sav' -File)+@(Get-ChildItem -LiteralPath "$project/Saved/SaveGames" -Filter 'VillageDefenses_*.sav' -File)
 $hashes=@{};foreach($file in $sources){
  $hashes[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName).Hash
 }
 $testSources=if($SaveDirectory){@(Get-ChildItem -LiteralPath $SaveDirectory -Filter '*.sav' -File)}else{$sources}
 foreach($file in $testSources){
  Copy-Item -LiteralPath $file.FullName -Destination "$run/Users/host/Saved/SaveGames/$($file.Name)"
  Copy-Item -LiteralPath $file.FullName -Destination "$run/OriginalSaveBackup/$($file.Name)"
 }
 $map="$project/Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap";$hashes[$map]=(Get-FileHash -LiteralPath $map).Hash
 @{protected_files=$hashes;module_sha256=(Get-FileHash -LiteralPath "$private/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;save_snapshot=$SaveDirectory;port=$port;lag_ms=60;loss_percent=2;render_clients=[bool]$RenderClients}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$run/inputs.json"
 $hostPeer=Launch host;WaitMarker "$run/host.log" 'GameNetDriver' $hostPeer
 $client=Launch client;WaitMarker "$run/Evidence/client-result.json" '' $client;ExitReceipt client $client
 if(-not(Get-Content -LiteralPath "$run/Evidence/client-result.json" -Raw|ConvertFrom-Json).passed){throw 'Initial client failed'}
 WaitMarker "$run/Evidence/late-join-ready.json" '' $hostPeer 60
 $late=Launch late;WaitMarker "$run/Evidence/late-result.json" '' $late;ExitReceipt late $late
 WaitMarker "$run/Evidence/host-result.json" '' $hostPeer 60;ExitReceipt host $hostPeer
 $functional=$true;foreach($role in 'host','client','late'){$functional=$functional -and (Get-Content -LiteralPath "$run/Evidence/$role-result.json" -Raw|ConvertFrom-Json).passed}
 $passed=$functional -and $script:CleanExits
 @{passed=$passed;functional_passed=$functional;clean_exits=$script:CleanExits;run=$run}|ConvertTo-Json|Set-Content -LiteralPath "$run/summary.json"
 Write-Output "HILLS_NETLOAD_DONE passed=$passed run=$run"
}catch{
 if(Test-Path -LiteralPath $run){@{error=$_.Exception.Message;at=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$run/failure.json"};throw
}finally{
 foreach($p in $owned){if(-not $p.HasExited){
  $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
  if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($private) -and $live.CommandLine.Contains('-HillsNetLoadAudit')){Stop-Process -Id $p.Id -ErrorAction SilentlyContinue;[void]$p.WaitForExit(10000)}
 }}
 if($hashes -and(Test-Path -LiteralPath $run)){
  $integrity=@{};foreach($file in $hashes.Keys){$integrity[$file]=((Get-FileHash -LiteralPath $file).Hash -eq $hashes[$file])}
  $integrity|ConvertTo-Json|Set-Content -LiteralPath "$run/protected-files-after.json"
 }
 if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
