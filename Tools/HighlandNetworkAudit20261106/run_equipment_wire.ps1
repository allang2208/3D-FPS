param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$swordRoot='D:/FPS3D/FPSGAME'
$swordStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$swordRun=Join-Path $PSScriptRoot "Wire/$swordStamp"
New-Item -ItemType Directory -Force -Path $swordRun | Out-Null
$swordPort=19991
while(Get-NetUDPEndpoint -LocalPort $swordPort -ErrorAction SilentlyContinue){$swordPort++}
$swordOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$swordGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$swordHeld=$false
$swordOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
function Start-SwordPeer([string]$role,[string]$map){
    $peerArgs=@(('"'+$swordRoot+'/FPSGAME.uproject"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-NoLiveCoding',
        '-SwordFinishWireAudit','-HighlandEquipmentWireAudit','-AssetGatherAll=false','-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',
        ('-ColdSteelProfile=SwordFinishWireAudit_'+$swordStamp+'_'+$role),('-port='+$swordPort),
        ('-UserDir="'+$swordRun+'/'+$role+'/"'),('-SwordFinishWireOutput="'+$swordRun+'/'+$role+'.json"'),
        ('-abslog="'+$swordRun+'/'+$role+'.log"'),'-ExecCmds="fps.body.AsyncPreload 0,t.MaxFPS 30"')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $swordOwned.Add($peer)
    @{role=$role;pid=$peer.Id;arguments=$peerArgs} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$swordRun/launch-$role.json" -Encoding utf8
    Write-Output "SWORD_WIRE_PEER $role PID=$($peer.Id)"
    return $peer
}
function Wait-SwordMarker([string]$marker,[System.Diagnostics.Process]$peer,[int]$seconds=240){
    $deadline=(Get-Date).AddSeconds($seconds)
    while((Get-Date) -lt $deadline){
        if((Test-Path -LiteralPath "$swordRun/host.log") -and (Select-String -LiteralPath "$swordRun/host.log" -SimpleMatch $marker -Quiet)){return}
        if($peer.HasExited){throw "Host exited before $marker"}
        if((Test-Path -LiteralPath "$swordRun/host.json") -and $marker -ne 'SWORD_FINISH_WIRE_FINISHED'){throw 'Wire fixture reported an early failure.'}
        Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for $marker"
}
try {
    while(-not $swordHeld){
        try{$swordHeld=$swordGate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$swordHeld=$true}
        if(-not $swordHeld){continue}
        $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','cl.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*') })
        if($busy.Count){$swordGate.ReleaseMutex();$swordHeld=$false;Start-Sleep -Seconds 10}
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    if(-not $SkipBuild){
        Write-Output "SWORD_WIRE_BUILD $swordRun"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$swordRoot/FPSGAME.uproject" -NoHotReloadFromIDE -MaxParallelActions=4 *> "$swordRun/build-editor.log"
        if($LASTEXITCODE -ne 0){throw "Editor build failed; read $swordRun/build-editor.log"}
    }
    @('Source/FPSGAME/Characters/FPSBodyRuneVisual.cpp','Source/FPSGAME/Characters/FPSPlayerBodyTypes.h','Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp',
      'Source/FPSGAME/Weapons/ModularSwordVisual.cpp','Source/FPSGAME/Development/SwordFinishWireAudit.cpp','Source/FPSGAME/Development/SwordFinishWireAudit.h',
      'Binaries/Win64/UnrealEditor-FPSGAME.dll','Content/Weapons/AzureRunesword20260913/M_AzureRunesword.uasset',
      'Content/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold.uasset') |
      ForEach-Object {
          $inputPath=Join-Path $swordRoot $_
          $inputStream=[IO.File]::OpenRead($inputPath);$inputHash=[Security.Cryptography.SHA256]::Create()
          try {[pscustomobject]@{Path=$inputPath;Hash=[BitConverter]::ToString($inputHash.ComputeHash($inputStream)).Replace('-','')}}
          finally {$inputStream.Dispose();$inputHash.Dispose()}
      } | ConvertTo-Json | Set-Content -LiteralPath "$swordRun/inputs.json" -Encoding utf8
    $hostOutput=Start-SwordPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.SwordFinishWireGameMode?listen'
    $hostPeer=$hostOutput[-1];$hostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SwordMarker 'SWORD_FINISH_WIRE_HOST_READY' $hostPeer
    $guestOutput=Start-SwordPeer 'client' ('127.0.0.1:'+$swordPort)
    $guestPeer=$guestOutput[-1];$guestOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SwordMarker 'SWORD_FINISH_WIRE_REJOIN_READY' $hostPeer 600
    if(-not $guestPeer.WaitForExit(30000)){throw 'First guest did not exit normally.'}
    $rejoinOutput=Start-SwordPeer 'rejoin' ('127.0.0.1:'+$swordPort);$rejoinOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-SwordMarker 'SWORD_FINISH_WIRE_FINISHED' $hostPeer
    $exits=@()
    foreach($peer in $swordOwned){if(-not $peer.WaitForExit(30000)){throw "Peer $($peer.Id) did not exit normally."};$exits+=@{pid=$peer.Id;exit_code=$peer.ExitCode}}
    $result=Get-Content -LiteralPath "$swordRun/host.json" -Raw | ConvertFrom-Json
    $ok=$result.passed -and -not @($exits | Where-Object {$_.exit_code -ne 0}).Count
    @{passed=$ok;run=$swordRun;transport='real local UDP listen host + guest + reconnect';port=$swordPort;peer_exits=$exits;rendered=$false;cases=$result.cases.Count} |
      ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$PSScriptRoot/wire-receipt.json" -Encoding utf8
    Write-Output "SWORD_WIRE_DONE PASS=$ok PATH=$swordRun"
    if(-not $ok){throw 'Wire audit failed.'}
} catch {
    @{passed=$false;run=$swordRun;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/wire-receipt.json" -Encoding utf8
    throw
} finally {
    foreach($peer in $swordOwned){if(-not $peer.HasExited){
        $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
        if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine -like '*-SwordFinishWireAudit*' -and $live.CommandLine -like ('*'+$swordStamp+'*')){Stop-Process -Id $peer.Id}
    }}
    $env:UE_SKIP_UBT_SDK_SETUP=$swordOldSdk
    if($swordHeld){$swordGate.ReleaseMutex()};$swordGate.Dispose()
}
