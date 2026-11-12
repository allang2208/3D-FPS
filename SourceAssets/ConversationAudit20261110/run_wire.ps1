param([switch]$Dedicated)
$ErrorActionPreference='Stop';$root='D:/FPS3D/FPSGAME';$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$mode=if($Dedicated){'dedicated'}else{'listen'};$run=Join-Path $root ('Saved/ConversationAudit20261110/Wire/'+$mode+'-'+$stamp)
New-Item -ItemType Directory -Force -Path $run | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false;$owned=[Collections.Generic.List[Diagnostics.Process]]::new()
$port=20210;while(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){$port++}
function Peer($role,$map){
    $args=@(('"'+$root+'/FPSGAME.uproject"'),('"'+$map+'"'),'-nullrhi','-nosound','-unattended','-nosplash','-NoLiveCoding','-SkillWireAudit','-LeapMovementWire',
        '-PktLag=80','-PktLoss=2',('-port='+$port),('-ColdSteelProfile=SkillNetworkAudit_LeapWire_'+$stamp+'_'+$role),('-UserDir="'+$run+'/'+$role+'-user/"'),
        ('-SkillWireOutput="'+$run+'/'+$role+'.json"'),('-abslog="'+$run+'/'+$role+'.log"'),'-ExecCmds="t.MaxFPS 60,p.NetShowCorrections 1"',
        '-LogCmds="LogNetPlayerMovement Verbose,LogRootMotion Log"',
        '-DPCVars=fps.body.AsyncPreload=0,Editor.AsyncSkinnedAssetCompilation=0,Editor.AsyncStaticMeshCompilation=0',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False')
    if($role -eq 'host' -and $Dedicated){$args+='-server'}else{$args+='-game'}
    $p=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $args -WindowStyle Hidden -PassThru;$owned.Add($p)
    $launchPath=Join-Path $run ('launch-'+$role+'.json')
    @{pid=$p.Id;arguments=$args;dll_sha256=(Get-FileHash ($root+'/Binaries/Win64/UnrealEditor-FPSGAME.dll')).Hash} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $launchPath -Encoding utf8
    if(-not (Test-Path -LiteralPath $launchPath)){throw 'Launch receipt was not saved.'}
    return $p
}
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    if(@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}).Count){throw 'Existing build preserved.'}
    $map='/Engine/Maps/Entry?game=/Script/FPSGAME.SkillWireAuditGameMode';if(-not $Dedicated){$map+='?listen'}
    $server=Peer 'host' $map;Write-Output "LEAP_WIRE_HOST pid=$($server.Id) path=$run"
    $deadline=[DateTime]::UtcNow.AddMinutes(5)
    do{if($server.HasExited -or [DateTime]::UtcNow -gt $deadline){throw 'Host startup failed.'};Start-Sleep -Seconds 1}
    until((Test-Path ($run+'/host.log')) -and (Select-String -LiteralPath ($run+'/host.log') -SimpleMatch 'SKILL_WIRE_HOST_READY' -Quiet))
    $client=Peer 'client' ('127.0.0.1:'+$port);Write-Output "LEAP_WIRE_CLIENT pid=$($client.Id)"
    $deadline=[DateTime]::UtcNow.AddMinutes(16)
    while(-not $server.HasExited){if([DateTime]::UtcNow -gt $deadline){throw 'Audit timeout.'};Start-Sleep -Seconds 2}
    if(-not $client.WaitForExit(30000)){throw 'Client failed to exit.'}
    $hostResult=Get-Content ($run+'/host.json') -Raw | ConvertFrom-Json;$clientResult=Get-Content ($run+'/client.json') -Raw | ConvertFrom-Json
    $passed=$hostResult.passed -and $clientResult.passed -and $server.ExitCode -eq 0 -and $client.ExitCode -eq 0
    @{passed=$passed;mode=$mode;port=$port;lag_ms=80;loss_percent=2;host_exit=$server.ExitCode;client_exit=$client.ExitCode;rendered=$false} | ConvertTo-Json | Set-Content ($run+'/receipt.json') -Encoding utf8
    Write-Output "LEAP_WIRE_DONE passed=$passed path=$run"
}finally{
    foreach($p in $owned){if(-not $p.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)";if($live.CommandLine -like '*-LeapMovementWire*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}}}
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
