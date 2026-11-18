param([string]$Attempt='udp01',[switch]$SkipBuild)
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$run="$project/Saved/HillsContinuity20261118/$Attempt"
$private="$run/Host";$port=20328
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[Collections.Generic.List[Diagnostics.Process]]::new()
function Launch([string]$Role,[switch]$Restart,[switch]$Rejoin){
 $label=if($Restart){'restart-'+$Role}elseif($Rejoin){'rejoin'}else{$Role}
 $dir="$run/Users/$Role";New-Item -ItemType Directory -Force -Path $dir|Out-Null
 $map=if($Role -eq 'host'){'/Game/GameMaps/L_TemperateHills_Initial?listen?HillsContinue'}else{'127.0.0.1:'+$port}
 $arguments=@(('"'+$private+'/FPSGAME.uproject"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
 '-HillsContinuityAudit','-HillsContinue','-SkipStartupMenu','-ClearwaterNoMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',('-port='+$port),
 ('-ColdSteelProfile=HillsContinuity_'+$Attempt+'_'+$Role),('-UserDir="'+$dir+'"'),('-abslog="'+$run+'/'+$label+'.log"'),
 ('-HillsContinuityOutput="'+$run+'/Evidence"'),'-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
 '-ExecCmds="t.MaxFPS 45,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,fps.Test.HillsContinuity"',
 '-LogCmds="LogFurnitureRest Verbose"',
 '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
 '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
 '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
 if($Restart){$arguments+='-HillsContinuityRestart'}
 $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
 $handle=$p.Handle;$owned.Add($p)
 @{pid=$p.Id;args=$arguments;role=$label}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$run/launch-$label.json"
 Write-Output "HILLS_CONTINUITY_STARTED $label pid=$($p.Id)"|Write-Host
 return $p
}
function Milestone([string]$Log,[string]$Marker,[Diagnostics.Process]$Peer,[int]$Seconds=1500){
 $end=[DateTime]::UtcNow.AddSeconds($Seconds)
 while([DateTime]::UtcNow -lt $end){
  if((Test-Path -LiteralPath $Log) -and (Select-String -LiteralPath $Log -SimpleMatch $Marker -Quiet)){return}
  if($Peer.HasExited){throw "Process exited before $Marker"};Start-Sleep -Seconds 2
 };throw "Timeout waiting for $Marker"
}
function ExitReceipt([string]$Role,[Diagnostics.Process]$Peer){
 [void]$Peer.WaitForExit(20000)
 $code=if($Peer.HasExited){$Peer.ExitCode}else{$null}
 @{pid=$Peer.Id;exited=$Peer.HasExited;exit_code=$code}|ConvertTo-Json|Set-Content -LiteralPath "$run/exit-$Role.json"
 if(-not $Peer.HasExited -or $code -ne 0){throw "$Role did not exit cleanly"}
}
function StopOwned([Diagnostics.Process]$Peer){
 if($Peer.HasExited){return}
 $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($Peer.Id)"
 if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($private) -and $live.CommandLine.Contains('-HillsContinuityAudit')){
  Stop-Process -Id $Peer.Id -ErrorAction SilentlyContinue;[void]$Peer.WaitForExit(10000)
 }
}
function WaitResult([string]$Name,[Diagnostics.Process]$Peer){
 $end=[DateTime]::UtcNow.AddMinutes(27)
 while(-not(Test-Path -LiteralPath "$run/Evidence/$Name-result.json")){
  if($Peer.HasExited -or [DateTime]::UtcNow -gt $end){throw "Missing $Name completion receipt"};Start-Sleep -Seconds 2
 }
 return Get-Content -LiteralPath "$run/Evidence/$Name-result.json" -Raw|ConvertFrom-Json
}
try {
 Write-Output 'Waiting for the existing UE batch gate.'
 try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
 if(Test-Path -LiteralPath $run){throw 'Attempt already exists; retain its evidence and use another name.'}
 New-Item -ItemType Directory -Force -Path "$run/Build","$run/Evidence"|Out-Null
 if(-not $SkipBuild){& "$project/Tools/WorldGeneration/Build-VillageDefenses.ps1" -OutputRoot "$run/Build"}
 if(-not $SkipBuild){foreach($target in 'FPSGAMEEditor','FPSGAME'){
  $receipt=Get-Content -LiteralPath "$run/Build/$target-build.json" -Raw|ConvertFrom-Json
  if($receipt.exit_code -ne 0){throw "$target build failed"}
 }}
 $busy=Get-CimInstance Win32_Process|Where-Object {$_.Name -in 'UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe'}
 if($busy){throw 'An engine process remains active; preserve it.'}
 if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Port occupied'}
 New-Item -ItemType Directory -Force -Path "$private/Binaries/Win64","$run/Users/host/Saved/SaveGames","$run/OriginalSaveBackup"|Out-Null
 Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$private/FPSGAME.uproject"
 Copy-Item -LiteralPath "$project/Config" -Destination "$private/Config" -Recurse
 $settings=@{Enabled='True';MaxAlive='3';MaxPerNight='3';WaveSize='3';ShrineDurability='150.0'}
 $inRaid=$false
 $config=foreach($line in Get-Content -LiteralPath "$private/Config/DefaultGame.ini"){
  if($line -match '^\[([^\]]+)\]'){$inRaid=$Matches[1] -eq 'TemperateHills.NightRaid'}
  if($inRaid -and $line -match '^([^=]+)='){
   $key=$Matches[1];if($settings.ContainsKey($key)){"$key=$($settings[$key])";continue}
  };$line
 }
 [IO.File]::WriteAllLines("$private/Config/DefaultGame.ini",[string[]]$config,[Text.UTF8Encoding]::new($false))
 foreach($folder in 'Content','Plugins','Shaders'){New-Item -ItemType Junction -Path "$private/$folder" -Target "$project/$folder"|Out-Null}
 foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$project/Binaries/Win64/$file" -Destination "$private/Binaries/Win64/$file"}
 $sources=@(Get-Item -LiteralPath "$project/Saved/SaveGames/TemperateHills_World.sav")+@(Get-ChildItem -LiteralPath "$project/Saved/SaveGames" -Filter 'HillsNight_*.sav' -File)+@(Get-ChildItem -LiteralPath "$project/Saved/SaveGames" -Filter 'VillageDefenses_*.sav' -File)
 $hashes=@{}
 foreach($file in $sources){
  $hashes[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName).Hash
  Copy-Item -LiteralPath $file.FullName -Destination "$run/Users/host/Saved/SaveGames/$($file.Name)"
  Copy-Item -LiteralPath $file.FullName -Destination "$run/OriginalSaveBackup/$($file.Name)"
 }
 $map="$project/Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap"
 $hashes[$map]=(Get-FileHash -LiteralPath $map).Hash
 @{protected_files=$hashes;module_sha256=(Get-FileHash -LiteralPath "$private/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;port=$port;lag_ms=60;loss_percent=2}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$run/inputs.json"
 $hostPeer=Launch host
 Milestone "$run/host.log" 'GameNetDriver' $hostPeer
 $client=Launch client
 Milestone "$run/host.log" 'HILLS_CONTINUITY_DISCONNECT_CLIENT' $hostPeer
 ExitReceipt client $client
 Milestone "$run/host.log" 'HILLS_CONTINUITY_REJOIN_READY' $hostPeer 180
 $rejoin=Launch client -Rejoin
 $initial=WaitResult initial $hostPeer
 ExitReceipt initial-host $hostPeer;ExitReceipt rejoin $rejoin
 if(-not $initial.passed){throw 'Initial native interaction/raid checks failed; see evidence.'}
 New-Item -ItemType Directory -Force -Path "$run/BeforeRestart"|Out-Null
 Get-ChildItem -LiteralPath "$run/Users/host/Saved/SaveGames" -Filter 'Hills*.sav' -File|Copy-Item -Destination "$run/BeforeRestart"
 # Compare the restart with the final teardown checkpoint. Living AI can move
 # between the earlier setup checkpoint and the host's orderly exit.
 $worldDigits=$initial.world_id.Replace('-','')
 Copy-Item -LiteralPath "$run/BeforeRestart/HillsNight_$worldDigits.sav" -Destination "$run/Users/host/Saved/SaveGames/HillsContinuityReference.sav"
 $hostPeer=Launch host -Restart
 Milestone "$run/restart-host.log" 'GameNetDriver' $hostPeer
 $client=Launch client -Restart
 $restart=WaitResult restart $hostPeer
 ExitReceipt restart-host $hostPeer;ExitReceipt restart-client $client
 $unchanged=$true;foreach($file in $hashes.Keys){$unchanged=$unchanged -and ((Get-FileHash -LiteralPath $file).Hash -eq $hashes[$file])}
 $warnings=@(Get-ChildItem -LiteralPath $run -Filter '*.log' -File|Select-String -Pattern 'SupportsObject.*TemperateHillsWorld|could not resolve the new relative movement base|Unable to resolve.*DynamicMeshComponent')
 $passed=$initial.passed -and $restart.passed -and $unchanged -and $warnings.Count -eq 0
 @{passed=$passed;initial_cases=$initial.checks.Count;restart_cases=$restart.checks.Count;terrain_netguid_warnings=$warnings.Count;protected_source_files_unchanged=$unchanged;world_id=$initial.world_id;seed=$initial.seed;natural_ai=$true;native_pew_E=$true;rendered=$false;lag_ms=60;loss_percent=2}|ConvertTo-Json|Set-Content -LiteralPath "$run/summary.json"
 Write-Output "HILLS_CONTINUITY_DONE passed=$passed run=$run"
}catch{
 @{error=$_.Exception.Message;at=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$run/failure.json"
 throw
}finally{
 foreach($p in $owned){StopOwned $p}
 if($hashes -and (Test-Path -LiteralPath $run)){
  $integrity=@{};foreach($file in $hashes.Keys){$integrity[$file]=((Get-FileHash -LiteralPath $file).Hash -eq $hashes[$file])}
  $integrity|ConvertTo-Json|Set-Content -LiteralPath "$run/protected-files-after.json"
 }
 if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
