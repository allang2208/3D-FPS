param([switch]$NativeOnly,[switch]$WireOnly)
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$taskDir="$project/SourceAssets/MeteorFormulaNetAudit20261022"
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$out="$taskDir/Wire/$stamp"
[void](New-Item -ItemType Directory -Force -Path $out)
$port=19947
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
function Start-MeteorPeer([string]$Role,[string]$Map){
    $arguments=@(('"'+$project+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-SkillWireAudit','-MeteorWireAudit',
      '-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0,[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False,[ConsoleVariables]:fps.body.AsyncPreload=0,[ConsoleVariables]:fps.body.WorldBodySuppress=1',
      ('-ColdSteelProfile=SkillNetworkAudit_'+$stamp+'_'+$Role),('-port='+$port),('-UserDir="'+$out+'/'+$Role+'/"'),
      ('-SkillWireOutput="'+$out+'/'+$Role+'.json"'),('-abslog="'+$out+'/'+$Role+'.log"'),
      '-ExecCmds="fps.body.AsyncPreload 0,t.MaxFPS 30,NetEmulation.PktLag 60,NetEmulation.PktLoss 3"')
    $peer=Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $owned.Add($peer);Write-Output "METEOR_WIRE_PEER $Role PID=$($peer.Id)";return $peer
}
function Wait-MeteorMarker([string]$Marker,[System.Diagnostics.Process]$Peer,[int]$Seconds){
    $until=(Get-Date).AddSeconds($Seconds)
    while((Get-Date)-lt $until){
        if((Test-Path -LiteralPath "$out/host.log") -and (Select-String -LiteralPath "$out/host.log" -SimpleMatch $Marker -Quiet)){return}
        if($Peer.HasExited){throw "Host exited before $Marker"};Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for $Marker"
}
try{
    Write-Output 'Queued for the shared UE audit batch.'
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    while($true){
        $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','cl.exe','link.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(@($busy | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Interactive editor is open; preserve it.'}
        if(-not $busy.Count){break};Write-Output 'Waiting for active UE/build process.';Start-Sleep -Seconds 10
    }
    if(-not $WireOnly){
        & $exe "$project/FPSGAME.uproject" -run=SkillNetworkAudit -MeteorFormulaNetOnly -nullrhi -unattended -nosound -nop4 -nosplash "-abslog=$out/native.log" *> "$out/native-output.log"
        if($LASTEXITCODE -ne 0){throw "Native audit failed: $out/native.log"}
        Copy-Item -LiteralPath "$taskDir/native-result.json" -Destination "$out/native-result.json"
        $native=Get-Content -LiteralPath "$out/native-result.json" -Raw | ConvertFrom-Json
        Write-Output "METEOR_NATIVE_FINISHED CHECKS=$($native.checks) FAILURES=$($native.failures)"
        if($native.failures -ne 0){throw 'Native audit reported failures.'}
    }
    if($NativeOnly){return}
    $free=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
    if($free -lt 12){throw "Need memory for two isolated peers; only $([math]::Round($free,1)) GiB available."}
    if(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){throw 'Audit port occupied.'}
    @('Binaries/Win64/UnrealEditor-FPSGAME.dll','Content/ColdSteelData/skills.json','Source/FPSGAME/Skills/MeteorWireAudit.cpp','Source/FPSGAME/Skills/MeteorGround.cpp','Source/FPSGAME/Skills/FPSMeteorStrike.cpp','Source/FPSGAME/Skills/FPSFireMagicComponent.cpp','Source/FPSGAME/Multiplayer/ColdSteelPlayerState.cpp') | ForEach-Object {Get-FileHash -LiteralPath (Join-Path $project $_)} | Select-Object Path,Hash | ConvertTo-Json | Set-Content -LiteralPath "$out/input-hashes.json" -Encoding utf8
    $started=Start-MeteorPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.SkillWireAuditGameMode?listen';$hostPeer=$started[-1];$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-MeteorMarker 'SKILL_WIRE_HOST_READY' $hostPeer 240
    $started=Start-MeteorPeer 'client' ('127.0.0.1:'+$port);$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-MeteorMarker 'METEOR_WIRE_RESULT' $hostPeer 240
    $hostResult=Get-Content -LiteralPath "$out/host.json" -Raw | ConvertFrom-Json
    $clientResult=if(Test-Path -LiteralPath "$out/client.json"){Get-Content -LiteralPath "$out/client.json" -Raw | ConvertFrom-Json}else{$null}
    $passed=$hostResult.passed -and $clientResult.passed
    @{directory=$out;passed=$passed;transport='UDP listen host + client';port=$port;lag_ms_each_peer=60;loss_percent_each_peer=3;rendered=$false;late_actor_relevancy=$true;full_profile_reconnect=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskDir/wire-receipt.json" -Encoding utf8
    Write-Output "METEOR_WIRE_FINISHED PASS=$passed PATH=$out"
    if(-not $passed){exit 1}
}finally{
    foreach($peer in $owned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)";if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-MeteorWireAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $peer.Id}}
    }
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
