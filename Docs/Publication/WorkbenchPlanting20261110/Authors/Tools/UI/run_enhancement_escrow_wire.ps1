param(
    [string]$Editor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe',
    [int]$Port=20079,
    [string]$OutputDirectory=''
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
if(!$OutputDirectory){$OutputDirectory=Join-Path $root ('Saved/EnhancementEscrowWire/'+$stamp)}
$out=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $out | Out-Null
if(Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue){throw "UDP port occupied: $Port"}
$session=[Guid]::NewGuid().ToString('N')
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$owned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-Peer([string]$Role,[string]$Map){
    $profile='EnhancementEscrowWireAudit_'+$stamp+'_'+$(if($Role -eq 'host'){'host'}else{'guest'})
    $userDir=Join-Path $out $(if($Role -eq 'host'){'host-user'}else{'guest-user'})
    $a=@(('"'+(Join-Path $root 'FPSGAME.uproject')+'"'),('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-NoShaderCompile',
        '-EnhancementEscrowWireAudit',('-EscrowWireSession='+$session),('-ColdSteelProfile='+$profile),('-port='+$Port),
        '-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-DPCVars=fps.body.WorldBodySuppress=1,fps.body.AsyncPreload=0,Editor.AsyncSkinnedAssetCompilation=0,Editor.AsyncStaticMeshCompilation=0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-UserDir="'+$userDir+'/"'),('-EscrowWireOutput="'+(Join-Path $out ($Role+'.json'))+'"'),
        ('-abslog="'+(Join-Path $out ($Role+'.log'))+'"'),'-ExecCmds="t.MaxFPS 30"')
    $p=Start-Process -FilePath $Editor -ArgumentList $a -WindowStyle Hidden -PassThru
    $owned.Add($p);@{role=$Role;pid=$p.Id;arguments=$a} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out ($Role+'-launch.json')) -Encoding utf8
    return $p
}
function Wait-Marker([string]$Marker,[System.Diagnostics.Process]$Server){
    $deadline=(Get-Date).AddMinutes(8)
    while((Get-Date) -lt $deadline){
        if((Test-Path -LiteralPath "$out/host.log") -and (Select-String -LiteralPath "$out/host.log" -SimpleMatch $Marker -Quiet)){return}
        if($Server.HasExited){throw "Host exited before $Marker"}
        Start-Sleep -Seconds 1
    }
    throw "Timed out waiting for $Marker"
}
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(!$held){throw 'Shared UE batch remained busy.'}
    # The parent performs the one combined build. Never start another build here.
    $server=Start-Peer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.EnhancementEscrowWireGameMode?listen'
    Wait-Marker 'ENHANCEMENT_WIRE_HOST_READY' $server
    $first=Start-Peer 'guest-first' ('127.0.0.1:'+$Port)
    Wait-Marker 'ENHANCEMENT_WIRE_RECONNECT_READY' $server
    if(!$first.WaitForExit(30000)){throw 'First client did not exit before reconnect.'}
    if($first.ExitCode -ne 0){throw "First client failed: $($first.ExitCode)"}
    $second=Start-Peer 'guest-reconnect' ('127.0.0.1:'+$Port)
    Wait-Marker 'ENHANCEMENT_WIRE_RESULT' $server
    $exits=@();foreach($p in $owned){if(!$p.WaitForExit(30000)){throw "Owned peer did not exit: $($p.Id)"};$exits+=@{pid=$p.Id;exit_code=$p.ExitCode}}
    $hostResult=Get-Content -LiteralPath "$out/host.json" -Raw | ConvertFrom-Json
    $firstResult=Get-Content -LiteralPath "$out/guest-first.json" -Raw | ConvertFrom-Json
    $secondResult=Get-Content -LiteralPath "$out/guest-reconnect.json" -Raw | ConvertFrom-Json
    $ok=$hostResult.passed -and $firstResult.passed -and $secondResult.passed -and !@($exits|Where-Object exit_code -ne 0).Count
    @{passed=$ok;directory=$out;cases=$hostResult.checks.Count;peer_exits=$exits;transport='local UDP; sequential same-profile reconnect';rendered=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out/wire-receipt.json" -Encoding utf8
    Write-Output "ENHANCEMENT_ESCROW_WIRE PASS=$ok PATH=$out"
    if(!$ok){exit 1}
}finally{
    foreach($p in $owned){
        if(!$p.HasExited){[void]$p.WaitForExit(5000)}
        if(!$p.HasExited){$live=Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)";if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-EnhancementEscrowWireAudit*' -and $live.CommandLine -like ('*'+$session+'*')){Stop-Process -Id $p.Id}}
    }
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
