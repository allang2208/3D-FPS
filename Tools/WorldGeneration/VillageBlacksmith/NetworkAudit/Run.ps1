param([string]$Attempt='udp01',[string]$Build='Build01',[string]$GameBuild='')
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$root="$project/Saved/HillsVillageInteractionAudit20261118"
$run="$root/$Attempt";$hostDir="$run/Host";$port=20318
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[Collections.Generic.List[Diagnostics.Process]]::new()
function Launch([string]$Role,[string]$Map,[switch]$Rejoin){
 $dir="$run/$Role";New-Item -ItemType Directory -Force -Path $dir|Out-Null
 $label=if($Rejoin){'rejoin'}else{$Role}
 $arguments=@(('"'+$hostDir+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
 '-HillsVillageInteractionAudit','-SkipStartupMenu','-ClearwaterNoMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',('-port='+$port),
 ('-ColdSteelProfile=HillsVillageAudit_'+$Attempt+'_'+$Role),('-UserDir="'+$dir+'"'),('-abslog="'+$run+'/'+$label+'.log"'),
 ('-HillsVillageAuditOutput="'+$run+'/Evidence"'),'-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
 '-ExecCmds="t.MaxFPS 45,fps.body.WorldBodySuppress 1,NetEmulation.PktLag 60,NetEmulation.PktLoss 2,fps.Test.HillsVillageInteractionAudit"',
 '-ini:Game:[TemperateHills.NightRaid]:Enabled=False',
 '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=180.0',
 '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=300.0',
 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
 '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
 if($Role -eq 'host'){$arguments+='-HillsNewWorld';$arguments+='-HillsSeed=1518277816'}
 $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
 $handle=$p.Handle;$owned.Add($p)
 @{pid=$p.Id;args=$arguments;role=$label}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$run/launch-$label.json"
 Write-Host "HILLS_VILLAGE_STARTED $label pid=$($p.Id)";return $p
}
function Marker([string]$Text,[Diagnostics.Process]$Peer,[int]$Seconds=1100){
 $end=[DateTime]::UtcNow.AddSeconds($Seconds)
 while([DateTime]::UtcNow -lt $end){
  if(Test-Path -LiteralPath "$run/Evidence/result.json"){throw 'Probe completed before milestone; inspect result.json'}
  if((Test-Path -LiteralPath "$run/host.log") -and (Select-String -LiteralPath "$run/host.log" -SimpleMatch $Text -Quiet)){return}
  if($Peer.HasExited){throw "Peer exited before $Text"};Start-Sleep -Seconds 2
 };throw "Timeout waiting for $Text"
}
function Stop-Owned([Diagnostics.Process]$P){
 if($P.HasExited){return};$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($P.Id)"
 if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($hostDir) -and $live.CommandLine.Contains('-HillsVillageInteractionAudit')){Stop-Process -Id $P.Id -ErrorAction SilentlyContinue;[void]$P.WaitForExit(10000)}
}
try{
 try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
 if(Test-Path -LiteralPath $run){throw 'Attempt already exists'}
 if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Port occupied'}
 foreach($target in 'FPSGAMEEditor','FPSGAME'){
  $receiptBuild=if($target -eq 'FPSGAME' -and $GameBuild){$GameBuild}else{$Build}
  $receipt=Get-Content -LiteralPath "$root/$receiptBuild/$target-build.json" -Raw|ConvertFrom-Json
  if($receipt.exit_code -ne 0){throw 'Build is incomplete'}
 }
 New-Item -ItemType Directory -Force -Path "$hostDir/Binaries/Win64","$run/Evidence"|Out-Null
 Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostDir/FPSGAME.uproject"
 Copy-Item -LiteralPath "$project/Config" -Destination "$hostDir/Config" -Recurse
 foreach($folder in 'Content','Plugins','Shaders'){New-Item -ItemType Junction -Path "$hostDir/$folder" -Target "$project/$folder"|Out-Null}
 foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){Copy-Item -LiteralPath "$project/Binaries/Win64/$file" -Destination "$hostDir/Binaries/Win64/$file"}
 $save="$project/Saved/SaveGames/TemperateHills_World.sav";$map="$project/Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap"
 $saveHash=(Get-FileHash -LiteralPath $save).Hash;$mapHash=(Get-FileHash -LiteralPath $map).Hash
 @{module_sha256=(Get-FileHash -LiteralPath "$hostDir/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;source_save_sha256=$saveHash;map_sha256=$mapHash}|ConvertTo-Json|Set-Content -LiteralPath "$run/inputs.json"
 $hostPeer=Launch 'host' '/Game/GameMaps/L_TemperateHills_Initial?listen'
 Marker 'GameNetDriver' $hostPeer
 $client=Launch 'client' ('127.0.0.1:'+$port)
 Marker 'HILLS_VILLAGE_DISCONNECT_CLIENT' $hostPeer
 [void]$client.WaitForExit(15000)
 if(-not $client.HasExited){throw 'Client failed to exit before reconnect'}
 @{pid=$client.Id;exit_code=$client.ExitCode}|ConvertTo-Json|Set-Content -LiteralPath "$run/exit-client.json"
 Marker 'HILLS_VILLAGE_RECONNECT_READY' $hostPeer 200
 $rejoin=Launch 'client' ('127.0.0.1:'+$port) -Rejoin
 $end=[DateTime]::UtcNow.AddMinutes(5)
 while(-not(Test-Path -LiteralPath "$run/Evidence/result.json")){
  if($hostPeer.HasExited -or [DateTime]::UtcNow -gt $end){throw 'Missing completion receipt'};Start-Sleep -Seconds 2
 }
 $cleanExit=$client.ExitCode -eq 0
 foreach($pair in @(@('host',$hostPeer),@('rejoin',$rejoin))){
  $p=$pair[1];[void]$p.WaitForExit(15000);@{pid=$p.Id;exited=$p.HasExited;exit_code=$p.ExitCode}|ConvertTo-Json|Set-Content -LiteralPath "$run/exit-$($pair[0]).json"
  $cleanExit=$cleanExit -and $p.HasExited -and ($p.ExitCode -eq 0)
 }
 $r=Get-Content -LiteralPath "$run/Evidence/result.json" -Raw|ConvertFrom-Json
 $unchanged=((Get-FileHash -LiteralPath $save).Hash -eq $saveHash) -and ((Get-FileHash -LiteralPath $map).Hash -eq $mapHash)
 $passed=$r.passed -and $cleanExit -and $unchanged
 @{passed=$passed;cases=$r.checks.Count;clean_exit=$cleanExit;source_save_and_map_unchanged=$unchanged;lag_ms=60;loss_percent=2;rendered=$false;natural_night_ai=$false;body_animation=$false}|ConvertTo-Json|Set-Content -LiteralPath "$run/summary.json"
 Write-Output "HILLS_VILLAGE_DONE passed=$passed run=$run"
}finally{foreach($p in $owned){Stop-Owned $p};if($held){$gate.ReleaseMutex()};$gate.Dispose()}
