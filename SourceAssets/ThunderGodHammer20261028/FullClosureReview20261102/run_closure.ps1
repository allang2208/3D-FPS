param([ValidateSet('Listen','Dedicated')][string]$Mode='Listen',[switch]$RenderedObserver,[switch]$Packaged,[switch]$EditorObserver,[switch]$HostInput,[switch]$HeadlessBodyHost)
$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$project='D:/FPS3D/ThunderHammerFullReviewHost20261102'
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
if($Packaged){$exe=Join-Path $PSScriptRoot 'Package/Windows/FPSGAME/Binaries/Win64/FPSGAME.exe'}
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss';$run=Join-Path $PSScriptRoot (($(if($Packaged){'Packaged-'}else{''}))+$Mode+'-'+$stamp)
New-Item -ItemType Directory -Path $run | Out-Null
$port=21371;while(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){$port++}
$owned=[Collections.Generic.List[Diagnostics.Process]]::new()
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
function Start-Peer([string]$role,[string]$map) {
    $peerProject=if($HeadlessBodyHost -and $role -eq 'host'){'D:/FPS3D/ThunderHammerHeadlessBodyHost20261103'}else{$project}
    # A packaged Game target does not become a dedicated-server target with -server.
    # Use the frozen editor commandlet host for authority, keeping cooked clients small.
    $editorServer=$Packaged -and $Mode -eq 'Dedicated' -and $role -eq 'host'
    $editorPeer=$editorServer -or ($EditorObserver -and $RenderedObserver -and $role -eq 'observer')
    $peerExe=if($editorPeer){'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'}else{$exe}
    $peerMinimum=if($Packaged){1.5MB}else{2.5MB}
    if($role -ne 'host' -and (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt $peerMinimum){throw "Insufficient memory before $role; preserving the partial run."}
    $saveRole=if($role -eq 'rejoin'){'client'}else{$role}
    $arguments=@(('"'+$peerProject+'/FPSGAME.uproject"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-NoLiveCoding','-NoShaderCompile','-AssetGatherAll=false','-ThunderHammerClosureAudit','-SkipStartupMenu',
      '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False','-DPCVars=fps.body.AsyncPreload=0,fps.body.WorldBodySuppress=1',
      ('-ColdSteelProfile=SkillNetworkAudit_TC_'+$stamp+'_'+$saveRole),('-port='+$port),
      ('-UserDir="'+$run.Replace('\','/')+'/'+$saveRole+'/"'),('-ThunderClosureOutput="'+$run+'/'+$role+'.json"'),
      ('-abslog="'+$run+'/'+$role+'.log"'),'-ExecCmds="t.MaxFPS 60,fps.body.WorldBodySuppress 1"')
    if($Packaged -and -not $editorPeer){$arguments=@($arguments | Where-Object {$_ -notlike '*FPSGAME.uproject*' -and $_ -ne '-game'})}
    if($HostInput -and $role -eq 'host'){
        # Suppressing the world body also disables its network presentation tick.
        # Keep it active for actual host-to-observer weapon/pose coverage.
        $arguments=@($arguments|ForEach-Object {$_.Replace('fps.body.WorldBodySuppress=1','fps.body.WorldBodySuppress=0').Replace('fps.body.WorldBodySuppress 1','fps.body.WorldBodySuppress 0')})
    }
    if($role -eq 'observer' -and $RenderedObserver){
        if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 9MB){throw 'Rendered observer needs 9 GiB free before launch.'}
        $arguments=@($arguments | Where-Object {$_ -notin @('-nullrhi','-NoShaderCompile')} | ForEach-Object {$_.Replace('fps.body.WorldBodySuppress=1','fps.body.WorldBodySuppress=0').Replace('fps.body.WorldBodySuppress 1','fps.body.WorldBodySuppress 0')})
        $arguments+='-RenderOffscreen';$arguments+=('-ThunderObserverCapture="'+$run.Replace('\','/')+'/ObserverFrames"')
    }
    if($role -eq 'host' -and $Mode -eq 'Dedicated'){$arguments+='-server'}
    if($role -eq 'observer'){$arguments+='-ThunderClosureObserver'}
    if($HostInput){$arguments+='-ThunderClosureHostInput'}
    if($role -eq 'rejoin'){$arguments+='-ThunderClosureRejoin'}
    $working=if($Packaged -and -not $editorPeer){Join-Path $PSScriptRoot 'Package/Windows'}else{$peerProject}
    $peer=Start-Process -FilePath $peerExe -WorkingDirectory $working -ArgumentList $arguments -WindowStyle Hidden -PassThru;$owned.Add($peer)
    $codeFile=if($editorPeer -or -not $Packaged){"$project/Binaries/Win64/UnrealEditor-FPSGAME.dll"}else{$peerExe}
    @{role=$role;pid=$peer.Id;arguments=$arguments;executable=$peerExe;code_file=$codeFile;code_sha256=(Get-FileHash $codeFile).Hash}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath "$run/launch-$role.json" -Encoding utf8
    Write-Output "THUNDER_CLOSURE_PEER $role PID=$($peer.Id)";return $peer
}
function Wait-Marker([string]$marker,[Diagnostics.Process]$peer,[int]$seconds=900) {
    $until=(Get-Date).AddSeconds($seconds);$low=0
    do {
        if((Test-Path -LiteralPath "$run/host.log") -and (Select-String -LiteralPath "$run/host.log" -SimpleMatch 'THUNDER_CLOSURE_FINISHED failed=' -Quiet)){throw 'Scenario reported a failed case; stopping owned peers without starting reconnect.'}
        if((Test-Path -LiteralPath "$run/host.log") -and (Select-String -LiteralPath "$run/host.log" -SimpleMatch $marker -Quiet)){return}
        if($peer.HasExited){throw "Host exited before $marker"}
        if((Get-Date) -gt $until){throw "Timed out before $marker"}
        if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 1MB){$low++}else{$low=0}
        if($low -ge 3){throw 'Run interrupted below 1 GiB free; partial evidence preserved.'}
        Start-Sleep -Seconds 2
    }while($true)
}
try {
    if($HeadlessBodyHost -and ($Packaged -or -not $HostInput)){throw 'HeadlessBodyHost is only for the two-editor host-input capture.'}
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no process started.'}
    $buildDeadline=(Get-Date).AddMinutes(20)
    while(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){
        if((Get-Date) -gt $buildDeadline){throw 'Build remained active; no runtime workload added.'}
        Start-Sleep -Seconds 5
    }
    $free=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB
    $requiredFree=if($RenderedObserver -and ($Packaged -or $HostInput)){12}elseif($RenderedObserver){16}elseif($Packaged){5}else{12}
    if($free -lt $requiredFree){throw "Only $([math]::Round($free,1)) GiB available. This scenario needs $requiredFree GiB initially plus a per-peer check; nothing started."}
    $map='/Engine/Maps/Entry?game=/Script/FPSGAME.ThunderHammerClosureGameMode';if($Mode -eq 'Listen'){$map+='?listen'}
    $hostOutput=Start-Peer 'host' $map;$hostPeer=$hostOutput[-1];$hostOutput|Where-Object {$_ -is [string]}|Write-Output
    Wait-Marker 'THUNDER_CLOSURE_HOST_READY' $hostPeer
    if(-not $HostInput){$clientOutput=Start-Peer 'client' ('127.0.0.1:'+$port);$clientOutput|Where-Object {$_ -is [string]}|Write-Output}
    Wait-Marker 'THUNDER_CLOSURE_LATE_READY' $hostPeer
    $observerOutput=Start-Peer 'observer' ('127.0.0.1:'+$port);$observerOutput|Where-Object {$_ -is [string]}|Write-Output
    if(-not $HostInput){
    Wait-Marker 'THUNDER_CLOSURE_REJOIN_READY' $hostPeer
    $firstClient=$clientOutput[-1];if(-not $firstClient.WaitForExit(20000)){throw 'Original client still running; preserving its save.'}
    $rejoinOutput=Start-Peer 'rejoin' ('127.0.0.1:'+$port);$rejoinOutput|Where-Object {$_ -is [string]}|Write-Output
    }
    Wait-Marker 'THUNDER_CLOSURE_FINISHED' $hostPeer
    $exits=@();foreach($p in $owned){if(-not $p.WaitForExit(30000)){throw "Peer $($p.Id) did not exit"};$exits+=@{pid=$p.Id;exit_code=$p.ExitCode}}
    $result=Get-Content -LiteralPath "$run/host.json" -Raw|ConvertFrom-Json
    $ok=$result.passed -and -not @($exits|Where-Object {$_.exit_code -ne 0}).Count
    $runtime=if($Packaged){$exe}else{"$project/Binaries/Win64/UnrealEditor-FPSGAME.dll"}
    @{passed=$ok;mode=$Mode;run=$run;exits=$exits;runtime=$runtime;runtime_sha256=(Get-FileHash $runtime).Hash;packaged=[bool]$Packaged;rendered=[bool]$RenderedObserver;host_input=[bool]$HostInput;audio=$false;profile_restart=(-not $HostInput)}|ConvertTo-Json -Depth 5|Set-Content "$run/receipt.json" -Encoding utf8
    Write-Output "THUNDER_CLOSURE_DONE PASS=$ok PATH=$run";if(-not $ok){exit 1}
} catch {
    @{passed=$false;run=$run;error=$_.Exception.Message}|ConvertTo-Json|Set-Content "$run/runner-error.json" -Encoding utf8
    throw
} finally {
    foreach($p in $owned){if(-not $p.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)";if($live.Name -in @('UnrealEditor-Cmd.exe','FPSGAME.exe') -and $live.CommandLine -like '*-ThunderHammerClosureAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}}}
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
