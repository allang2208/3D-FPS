param([switch]$SkipBuild,[switch]$IsolatedOnly)
$ErrorActionPreference='Stop'
$kukriProject='D:/FPS3D/FPSGAME'
$kukriStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$kukriOut=Join-Path $kukriProject ('SourceAssets/KukriFrostRaven20261028/CompletionAudit/'+$kukriStamp)
[void](New-Item -ItemType Directory -Force -Path $kukriOut)
$kukriExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$kukriGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$kukriHeld=$false
$kukriOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$kukriPort=19963
function Start-KukriPeer([string]$Role,[string]$Map) {
    $args=@(('"'+$kukriProject+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-KukriRuneWireAudit',
      '-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0','-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
      ('-ColdSteelProfile=SkillNetworkAudit_KukriWire_'+$kukriStamp+'_'+$Role),('-port='+$kukriPort),('-UserDir="'+$kukriOut+'/'+$Role+'/"'),
      ('-KukriRuneWireOutput="'+$kukriOut+'/'+$Role+'.json"'),('-abslog="'+$kukriOut+'/'+$Role+'.log"'),
      '-ExecCmds="t.MaxFPS 30,NetEmulation.PktLag 60,NetEmulation.PktLoss 3"')
    $peer=Start-Process -FilePath $kukriExe -ArgumentList $args -WindowStyle Hidden -PassThru
    $kukriOwned.Add($peer);Write-Output "KUKRI_PEER $Role PID=$($peer.Id)";return $peer
}
function Wait-KukriMarker([string]$Marker,[System.Diagnostics.Process]$Peer,[int]$Seconds) {
    $until=(Get-Date).AddSeconds($Seconds)
    while((Get-Date)-lt $until) {
        if((Test-Path -LiteralPath "$kukriOut/host.log") -and (Select-String -LiteralPath "$kukriOut/host.log" -SimpleMatch $Marker -Quiet)){return}
        if($Peer.HasExited){throw "Host exited before $Marker"}
        Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for $Marker"
}
try {
    Write-Output "KUKRI_AUDIT_OUTPUT $kukriOut"
    try{$kukriHeld=$kukriGate.WaitOne()}catch [Threading.AbandonedMutexException]{$kukriHeld=$true}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','cl.exe','link.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
    if($busy.Count){throw 'Existing UE or build process is active; preserved without interruption.'}
    if(-not $SkipBuild){
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$kukriProject/FPSGAME.uproject" -NoHotReloadFromIDE "-Log=$kukriOut/build-editor.log" *> "$kukriOut/build-console.log"
        if($LASTEXITCODE -ne 0){throw "Build failed: $kukriOut/build-console.log"}
        Write-Output 'KUKRI_BUILD_COMPLETE'
    }
    $audit=Start-Process -FilePath $kukriExe -WindowStyle Hidden -PassThru -ArgumentList @(
      ('"'+$kukriProject+'/FPSGAME.uproject"'),'-run=KukriNetworkAudit',('-Output="'+$kukriOut+'/isolated.json"'),
      '-nullrhi','-nosound','-unattended','-nosplash','-NoLiveCoding',('-abslog="'+$kukriOut+'/isolated.log"'))
    $kukriOwned.Add($audit);$audit.WaitForExit()
    if($audit.ExitCode -ne 0){throw "Isolated audit failed: $($audit.ExitCode)"}
    Write-Output 'KUKRI_ISOLATED_COMPLETE'
    if($IsolatedOnly){return}
    if(Get-NetUDPEndpoint -LocalPort $kukriPort -ErrorAction SilentlyContinue){throw 'Audit port occupied.'}
    $started=Start-KukriPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.KukriRuneWireGameMode?listen'
    $kukriHost=$started[-1];$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-KukriMarker 'KUKRI_WIRE_HOST_READY' $kukriHost 240
    $started=Start-KukriPeer 'client' ('127.0.0.1:'+$kukriPort);$started | Where-Object {$_ -is [string]} | Write-Output
    Wait-KukriMarker 'KUKRI_WIRE_FINISHED' $kukriHost 240
    $wire=Get-Content -LiteralPath "$kukriOut/host.json" -Raw | ConvertFrom-Json
    $isolated=Get-Content -LiteralPath "$kukriOut/isolated.json" -Raw | ConvertFrom-Json
    @{directory=$kukriOut;wire_passed=$wire.passed;isolated_checks=$isolated.checks.Count;isolated_failures=$isolated.failures;
      transport='UDP listen host and client';lag_ms_each_peer=60;loss_percent_each_peer=3;rendered=$false;reconnect_tested=$false;
      wire_scope='rune component state with isolated profiles; attack RPC validation is isolated'} | ConvertTo-Json | Set-Content -LiteralPath "$kukriOut/receipt.json" -Encoding utf8
    Write-Output "KUKRI_AUDIT_COMPLETE wire=$($wire.passed) isolated=$($isolated.checks.Count)"
    if(-not $wire.passed){throw 'Rune wire cases failed; see host.json.'}
} finally {
    foreach($peer in $kukriOwned){
        if(-not $peer.HasExited){[void]$peer.WaitForExit(5000)}
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like ('*'+$kukriStamp+'*')){Stop-Process -Id $peer.Id}
        }
    }
    if($kukriHeld){$kukriGate.ReleaseMutex()};$kukriGate.Dispose()
}
