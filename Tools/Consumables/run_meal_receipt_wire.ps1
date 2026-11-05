param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$mealWireRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$mealOutput=Join-Path $mealWireRoot 'Saved/MealNetworkReview'
if(-not $env:UE_ROOT){throw 'Set UE_ROOT to the installed UE 5.8 root.'}
$mealEditor=Join-Path $env:UE_ROOT 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$mealWireStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$mealWireDir=Join-Path $mealOutput ('Wire/'+$mealWireStamp)
New-Item -ItemType Directory -Force -Path $mealWireDir | Out-Null
$mealWirePort=19986
if(Get-NetUDPEndpoint -LocalPort $mealWirePort -ErrorAction SilentlyContinue){throw 'MealReceipt presentation audit port occupied.'}
$mealWireGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$mealWireHeld=$false
$mealWireOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$mealWireSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Start-MealReceiptPeer([string]$role,[string]$map){
    $peerArgs=@(('"'+(Join-Path $mealWireRoot 'FPSGAME.uproject')+'"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-NoShaderCompile',
        '-ShotgunWireAudit','-MealReceiptWire','-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-DPCVars=fps.body.AsyncPreload=0,Editor.AsyncSkinnedAssetCompilation=0,Editor.AsyncStaticMeshCompilation=0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=ShotgunWireAudit_'+$mealWireStamp+'_'+$role),('-port='+$mealWirePort),
        ('-UserDir="'+$mealWireDir+'/'+$role+'/"'),('-ShotgunWireOutput="'+(Join-Path $mealWireDir ($role+'.json'))+'"'),
        ('-abslog="'+(Join-Path $mealWireDir ($role+'.log'))+'"'),'-ExecCmds="t.MaxFPS 30"')
    $peer=Start-Process -FilePath $mealEditor -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $mealWireOwned.Add($peer);Write-Output "MealReceipt_WIRE_PEER $role PID=$($peer.Id)";return $peer
}
function Wait-MealReceiptMarker([string]$marker,[System.Diagnostics.Process]$server){
    $deadline=(Get-Date).AddMinutes(7)
    while((Get-Date) -lt $deadline){
        if((Test-Path -LiteralPath "$mealWireDir/host.log") -and (Select-String -LiteralPath "$mealWireDir/host.log" -SimpleMatch $marker -Quiet)){return}
        if($server.HasExited){throw "Audit host exited before $marker"}
        Start-Sleep -Seconds 1
    }
    throw "Audit timeout waiting for $marker"
}
try{
    Write-Output 'Waiting for the shared UE batch.'
    try{$mealWireHeld=$mealWireGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$mealWireHeld=$true}
    if(-not $mealWireHeld){throw 'Existing UE batch remained busy.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    if(-not $SkipBuild){
        $deadline=(Get-Date).AddMinutes(10)
        do{
            $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor-Cmd.exe','dotnet.exe','UnrealBuildTool.exe')) -and $_.CommandLine -like '*FPSGAME*'})
            if($busy.Count){if((Get-Date) -gt $deadline){throw 'Existing project build remained active.'};Start-Sleep -Seconds 5}
        }while($busy.Count)
        & "$mealWireRoot/Tools/Build/Build-Editor.ps1" *> (Join-Path $mealWireDir 'build-editor.log')
        Get-Content -LiteralPath (Join-Path $mealWireDir 'build-editor.log') -Tail 7
    }
    $hostOutput=Start-MealReceiptPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ShotgunWireAuditGameMode?listen';$hostPeer=$hostOutput[-1]
    $hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-MealReceiptMarker 'SHOTGUN_WIRE_HOST_READY' $hostPeer
    $clientOutput=Start-MealReceiptPeer 'client' ('127.0.0.1:'+$mealWirePort);$clientPeer=$clientOutput[-1]
    $clientOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-MealReceiptMarker 'SHOTGUN_WIRE_RESULT' $hostPeer
    $peerExits=@()
    foreach($peer in $mealWireOwned){
        if(-not $peer.WaitForExit(30000)){throw "Audit peer PID=$($peer.Id) did not exit normally after its final result."}
        $peerExits+=@{pid=$peer.Id;exit_code=$peer.ExitCode}
    }
    $result=Get-Content -LiteralPath "$mealWireDir/host.json" -Raw | ConvertFrom-Json
    $complete=$result.passed -and -not @($peerExits | Where-Object { $_.exit_code -ne 0 }).Count
    @{directory=$mealWireDir;passed=$complete;cases=$result.cases;peer_exits=$peerExits;transport='local UDP owner and listen host; delayed contact receipt';port=$mealWirePort;lag_ms_each_peer=65;loss_percent_each_peer=5;rendered=$false} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $mealWireDir 'wire-receipt.json') -Encoding utf8
    Write-Output "MealReceipt_WIRE_FINISHED PASS=$complete PATH=$mealWireDir"
    if(-not $complete){exit 1}
}finally{
    foreach($peer in $mealWireOwned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-MealReceiptWire*' -and $live.CommandLine -like ('*'+$mealWireStamp+'*')){Stop-Process -Id $peer.Id}
        }
    }
    $env:UE_SKIP_UBT_SDK_SETUP=$mealWireSdk
    if($mealWireHeld){$mealWireGate.ReleaseMutex()};$mealWireGate.Dispose()
}
