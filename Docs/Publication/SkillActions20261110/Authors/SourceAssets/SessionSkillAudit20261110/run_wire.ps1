param([ValidateSet('ChainSlash','Conversation','StarMarrow','FlameArmor')][string]$Case='ChainSlash',[switch]$Dedicated,[string]$ProjectRoot='D:/FPS3D/FPSGAME')
$ErrorActionPreference='Stop'
$project=$ProjectRoot;$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss';$mode=if($Dedicated){'dedicated'}else{'listen'}
$run=Join-Path $PSScriptRoot ('Wire/'+$Case+'-'+$mode+'-'+$stamp)
New-Item -ItemType Directory -Force -Path $run | Out-Null
$port=20060;while(Get-NetUDPEndpoint -LocalPort $port -ErrorAction SilentlyContinue){$port++}
$flag=switch($Case){ChainSlash{'-SessionChainWire'}Conversation{'-ConversationCombatWire'}StarMarrow{'-StarMarrowWireAudit'}FlameArmor{'-FlameArmorWireAudit'}}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-Peer([string]$role,[string]$map){
    $args=@(('"'+$project+'/FPSGAME.uproject"'),('"'+$map+'"'),'-nullrhi','-nosound','-unattended','-nosplash','-Multiprocess','-NoLiveCoding','-SkillWireAudit',$flag,
        '-PktLag=80','-PktLoss=2',('-ColdSteelProfile=SkillNetworkAudit_Conversation_'+$stamp+'_'+$role),('-port='+$port),
        ('-UserDir="'+$run+'/'+$role+'/"'),('-SkillWireOutput="'+$run+'/'+$role+'.json"'),('-abslog="'+$run+'/'+$role+'.log"'),'-ExecCmds="t.MaxFPS 30"',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False')
    if($role -eq 'host' -and $Dedicated){$args+=@('-server','-StarDedicatedAudit')}else{$args+='-game'}
    $p=Start-Process -FilePath $exe -ArgumentList $args -WindowStyle Hidden -PassThru;$owned.Add($p)
    @{pid=$p.Id;role=$role;arguments=$args} | ConvertTo-Json | Set-Content -LiteralPath "$run/launch-$role.json" -Encoding utf8
    Write-Output "WIRE_PEER $Case $mode $role PID=$($p.Id)";return $p
}
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no peers started.'}
    if(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    $map='/Engine/Maps/Entry?game=/Script/FPSGAME.SkillWireAuditGameMode';if(-not $Dedicated){$map+='?listen'}
    $launch=Start-Peer 'host' $map;$server=$launch[-1];$launch | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(5)
    do{
        if($server.HasExited){throw 'Host exited before ready.'}
        if([DateTime]::UtcNow -gt $deadline){throw 'Host startup timeout.'}
        Start-Sleep -Seconds 1
    }until((Test-Path -LiteralPath "$run/host.log") -and (Select-String -LiteralPath "$run/host.log" -SimpleMatch 'SKILL_WIRE_HOST_READY' -Quiet))
    $launch=Start-Peer 'client' ('127.0.0.1:'+$port);$launch | Where-Object {$_ -is [string]} | Write-Output
    $deadline=[DateTime]::UtcNow.AddMinutes(6)
    while(-not(Test-Path -LiteralPath "$run/host.json")){
        if($server.HasExited){throw 'Host exited before result.'}
        if([DateTime]::UtcNow -gt $deadline){throw 'Network review timed out.'}
        Start-Sleep -Seconds 1
    }
    $exits=@();foreach($p in $owned){if(-not $p.WaitForExit(30000)){throw "Peer $($p.Id) failed to exit normally."};$exits+=@{pid=$p.Id;exit_code=$p.ExitCode}}
    $result=Get-Content -LiteralPath "$run/host.json" -Raw | ConvertFrom-Json
    $passed=$result.passed -and (Test-Path -LiteralPath "$run/client.json") -and -not @($exits | Where-Object {$_.exit_code -ne 0}).Count
    @{passed=$passed;case=$Case;mode=$mode;run=$run;port=$port;configured_lag_ms=80;configured_loss_percent=2;rendered=$false;peer_exits=$exits} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$run/receipt.json" -Encoding utf8
    Write-Output "WIRE_DONE PASS=$passed PATH=$run"
    if(-not $passed){exit 1}
}finally{
    foreach($p in $owned){if(-not $p.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)";
        if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-SkillWireAudit*' -and $live.CommandLine -like ('*'+$stamp+'*')){Stop-Process -Id $p.Id}}}
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
