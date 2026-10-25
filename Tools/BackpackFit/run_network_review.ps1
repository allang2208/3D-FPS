param([switch]$SkipBuild,[string[]]$Packs=@('ue_simple_sling_bag','ue_portable_backpack','ue_mountain_backpack','ue_expedition_backpack','ue_pathfinder_backpack','ue_farreach_backpack','ue_special_duty_backpack'))
$ErrorActionPreference='Stop'
$packProject='D:/FPS3D/FPSGAME'
$packStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$packRoot=Join-Path $packProject ('SourceAssets/BackpackFit20261024/NetworkReview/Run_'+$packStamp)
New-Item -ItemType Directory -Path $packRoot -Force | Out-Null
if(-not $SkipBuild){
    & (Join-Path $packProject 'Tools/WorkwearSet/build.ps1') -ReceiptRoot ('SourceAssets/BackpackFit20261024/NetworkReview/Build_'+$packStamp)
    if($LASTEXITCODE -ne 0){throw 'Build failed; peers not started'}
}
$packGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$packHeld=$false
$packOwned=[Collections.Generic.List[Diagnostics.Process]]::new();$packResults=@();$packPort=19946
function Start-PackPeer([string]$Role,[string]$Map){
    $packProfileRole=if($Role -eq 'rejoin'){'client'}else{$Role}
    $packArgs=@(('"'+$packProject+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-BackpackWireAudit',
      ('-BackpackWirePack='+$script:packTarget),('-ColdSteelProfile=BackpackAudit_'+$packStamp+'_'+$script:packTarget+'_'+$packProfileRole),('-port='+$packPort),
      ('-UserDir="'+$script:packCaseOut+'/'+$packProfileRole+'/"'),('-BackpackWireOutput="'+$script:packCaseOut+'/'+$Role+'.json"'),('-abslog="'+$script:packCaseOut+'/'+$Role+'.log"'),
      '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
      '-ExecCmds="fps.body.AsyncPreload 1,t.MaxFPS 30,NetEmulation.PktLag 60,NetEmulation.PktLoss 3"')
    if($script:packObserve){$packArgs+='-BackpackWireObserverCheck'}
    if($Role -eq 'rejoin'){$packArgs+='-BackpackWireReconnect'}
    $packPeer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $packArgs -WindowStyle Hidden -PassThru
    $packOwned.Add($packPeer);Write-Output "BACKPACK_PEER $script:packTarget $Role PID=$($packPeer.Id)";return $packPeer
}
function Wait-PackMarker([string]$Marker,[Diagnostics.Process]$HostPeer,[int]$Seconds=720){
    $packDeadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    while([DateTime]::UtcNow -lt $packDeadline){
        if((Test-Path -LiteralPath "$script:packCaseOut/host.log") -and (Select-String -LiteralPath "$script:packCaseOut/host.log" -SimpleMatch $Marker -Quiet)){return}
        if($HostPeer.HasExited){throw "Host exited before $Marker"};Start-Sleep -Seconds 2
    }
    throw "Timed out waiting for $Marker"
}
function Close-PackPeers {
    $packMemory=@()
    foreach($packPeer in $packOwned){
        if(-not $packPeer.HasExited){$packPeer.Refresh();$packMemory+=@{pid=$packPeer.Id;peak_working_set_gib=[Math]::Round($packPeer.PeakWorkingSet64/1GB,3);private_gib=[Math]::Round($packPeer.PrivateMemorySize64/1GB,3)}}
        if(-not $packPeer.HasExited){[void]$packPeer.WaitForExit(5000)}
        if(-not $packPeer.HasExited){
            $packLive=Get-CimInstance Win32_Process -Filter "ProcessId=$($packPeer.Id)"
            if($packLive.Name -eq 'UnrealEditor-Cmd.exe' -and $packLive.CommandLine -like '*-BackpackWireAudit*' -and $packLive.CommandLine -like ('*'+$packStamp+'*')){Stop-Process -Id $packPeer.Id;if(-not $packPeer.WaitForExit(30000)){throw 'Owned peer did not release its process after termination'}}
        }
    }
    if($packMemory.Count){$packMemory | ConvertTo-Json | Set-Content -LiteralPath "$script:packCaseOut/peer-memory.json" -Encoding utf8}
    $packOwned.Clear()
}
try {
    try{$packHeld=$packGate.WaitOne()}catch [Threading.AbandonedMutexException]{$packHeld=$true}
    while($true){
        $packBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match 'D:[\/]FPS3D[\/]FPSGAME[\/]FPSGAME\.uproject') -or
            $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if(@($packBusy | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Preserve the open editor; no peers started'}
        if(-not $packBusy.Count){break}
        try{Wait-Process -Id $packBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $packBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    @('Binaries/Win64/UnrealEditor-FPSGAME.dll','Content/ColdSteelData/items.json','Content/ColdSteelData/player_body.json','Content/ColdSteelData/modular_outfits.json','Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp','Source/FPSGAME/Characters/FPSPlayerBodyAppearance.cpp','Source/FPSGAME/Development/BackpackWireAudit.cpp') |
        ForEach-Object {Get-FileHash -LiteralPath (Join-Path $packProject $_)} | Select-Object Path,Hash | ConvertTo-Json | Set-Content -LiteralPath "$packRoot/input-hashes.json" -Encoding utf8
    foreach($script:packTarget in $Packs){
        if($script:packTarget -notmatch '^ue_[a-z_]+$'){throw 'Invalid pack ID'}
        $script:packCaseOut=Join-Path $packRoot $script:packTarget;New-Item -ItemType Directory -Path $script:packCaseOut -Force | Out-Null
        $script:packObserve=$script:packTarget -eq 'ue_special_duty_backpack'
        try {
            if(Get-NetUDPEndpoint -LocalPort $packPort -ErrorAction SilentlyContinue){throw 'Preserve occupied audit port'}
            $packMemoryDeadline=[DateTime]::UtcNow.AddSeconds(90)
            do {
                $packMemoryInfo=Get-CimInstance Win32_OperatingSystem
                $packFree=$packMemoryInfo.FreePhysicalMemory/1MB
                $packCommitFree=$packMemoryInfo.FreeVirtualMemory/1MB
                $packEnough=$packFree -ge 12 -and $packCommitFree -ge $(if($script:packObserve){28}else{20})
                if(-not $packEnough){Start-Sleep -Seconds 3}
            } while(-not $packEnough -and [DateTime]::UtcNow -lt $packMemoryDeadline)
            if(-not $packEnough){throw 'Insufficient physical/commit headroom for isolated peers'}
            $packStarted=Start-PackPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.BackpackWireAuditGameMode?listen';$packHost=$packStarted[-1];$packStarted | Where-Object {$_ -is [string]} | Write-Output
            Wait-PackMarker 'BACKPACK_WIRE_HOST_READY' $packHost 240
            $packStarted=Start-PackPeer 'client' ('127.0.0.1:'+$packPort);$packClient=$packStarted[-1];$packStarted | Where-Object {$_ -is [string]} | Write-Output
            if($script:packObserve){
                Wait-PackMarker 'BACKPACK_WIRE_OBSERVER_READY' $packHost
                $packStarted=Start-PackPeer 'observer' ('127.0.0.1:'+$packPort+'?BackpackObserver=1');$packStarted | Where-Object {$_ -is [string]} | Write-Output
            }
            Wait-PackMarker 'BACKPACK_WIRE_REJOIN_READY' $packHost
            if(-not $packClient.WaitForExit(30000)){throw 'Initial client did not exit'}
            $packStarted=Start-PackPeer 'rejoin' ('127.0.0.1:'+$packPort);$packStarted | Where-Object {$_ -is [string]} | Write-Output
            Wait-PackMarker 'BACKPACK_WIRE_RESULT' $packHost
            Close-PackPeers
            $packResult=Get-Content -LiteralPath "$script:packCaseOut/host.json" -Raw | ConvertFrom-Json
            foreach($packRole in @('client','rejoin')){
                $packClientResult=Get-Content -LiteralPath "$script:packCaseOut/$packRole.json" -Raw | ConvertFrom-Json
                $packResult.passed=$packResult.passed -and $packClientResult.passed
            }
            $packResults+=@{pack=$script:packTarget;passed=$packResult.passed;cases=$packResult.cases.Count;observer=$script:packObserve;directory=$script:packCaseOut}
            Write-Output "BACKPACK_NETWORK_CASE $script:packTarget passed=$($packResult.passed) cases=$($packResult.cases.Count)"
        } catch {
            $packResults+=@{pack=$script:packTarget;passed=$false;error=$_.Exception.Message;directory=$script:packCaseOut};Write-Output "BACKPACK_NETWORK_ERROR $script:packTarget $($_.Exception.Message)"
        } finally {Close-PackPeers}
        @{cases=$packResults;lag_ms_each_peer=60;loss_percent_each_peer=3;gravity='normal';async_preload=$true;rendered=$false} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$packRoot/summary.json" -Encoding utf8
    }
    Write-Output "BACKPACK_NETWORK_OUTPUT $packRoot"
    if(@($packResults | Where-Object {-not $_.passed}).Count){exit 1}
} finally {Close-PackPeers;if($packHeld){$packGate.ReleaseMutex()};$packGate.Dispose()}
