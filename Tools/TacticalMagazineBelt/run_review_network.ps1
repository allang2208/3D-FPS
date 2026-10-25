param([string]$Plugin='E:/FPSGAMEAssetCache/TacticalMagazineBeltReview20261024/PluginBuild01/HostProject/Plugins/TacticalBeltReview/TacticalBeltReview.uplugin')
$ErrorActionPreference='Stop'
$beltProject='D:/FPS3D/FPSGAME';$beltStamp=Get-Date -Format 'yyyyMMdd-HHmmss';$beltPort=19949
$beltReviewRoot=Join-Path $beltProject ('SourceAssets/TacticalMagazineBelt20261024/Review20261024/Network_'+$beltStamp)
New-Item -ItemType Directory -Path (Join-Path $beltReviewRoot 'results') -Force | Out-Null
$beltPeers=[Collections.Generic.List[Diagnostics.Process]]::new();$beltRows=@()
function Set-BeltPhase([int]$Phase,[string]$ExitRole='') {
    $beltControl=Join-Path $beltReviewRoot 'control.json';$beltTemp=Join-Path $beltReviewRoot 'control.tmp'
    @{phase=$Phase;exit_role=$ExitRole} | ConvertTo-Json | Set-Content -LiteralPath $beltTemp -Encoding UTF8
    Move-Item -LiteralPath $beltTemp -Destination $beltControl -Force
}
function Start-BeltPeer([string]$Role,[switch]$Rejoin) {
    $beltMap=if($Role -eq 'host'){'/Engine/Maps/Entry?game=/Script/FPSGAME.BackpackWireAuditGameMode?listen'}else{'127.0.0.1:'+$beltPort}
    $beltLabel=if($Rejoin){'rejoin'}else{$Role}
    $beltArgs=@(('"'+$beltProject+'/FPSGAME.uproject"'),('"'+$beltMap+'"'),'-game','-nullrhi','-RenderOffscreen','-nosound','-unattended','-nosplash','-NoAssetRegistryCache','-TacticalBeltAudit',
        ('-BeltCurveMetadata="'+$beltProject+'/SourceAssets/TacticalMagazineBelt20261024/Review20261024/uncooked-curve-metadata.json"'),
        ('-plugin="'+$Plugin+'"'),'-EnablePlugins=TacticalBeltReview',('-BeltReviewDirectory="'+$beltReviewRoot+'"'),('-BeltReviewRole='+$Role),
        ('-ColdSteelProfile=BeltAudit_'+$beltStamp+'_'+$Role),('-port='+$beltPort),('-UserDir="'+$beltReviewRoot+'/'+$Role+'/"'),('-abslog="'+$beltReviewRoot+'/'+$beltLabel+'.log"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ExecCmds="fps.body.AsyncPreload 1,t.MaxFPS 25,NetEmulation.PktLag 60,NetEmulation.PktLoss 3"')
    if($Rejoin){$beltArgs+='-BeltReviewRejoin'}
    $beltPeer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $beltArgs -WindowStyle Hidden -PassThru
    $beltPeers.Add($beltPeer);Write-Output "BELT_REVIEW_PEER $beltLabel PID=$($beltPeer.Id)";return $beltPeer
}
function Wait-BeltPhase([int]$Phase,[string[]]$Roles=@('host','client')) {
    $beltDeadline=[DateTime]::UtcNow.AddSeconds(240)
    while([DateTime]::UtcNow -lt $beltDeadline) {
        $beltResults=@();$beltReady=$true
        foreach($beltRole in $Roles) {
            $beltFile=Join-Path $beltReviewRoot ('results/'+$beltRole+'_'+$Phase.ToString('00')+'.json')
            if(-not (Test-Path -LiteralPath $beltFile)){$beltReady=$false;break}
            try{$beltResult=Get-Content -LiteralPath $beltFile -Raw | ConvertFrom-Json}catch{$beltReady=$false;break}
            $beltResults+=$beltResult
        }
        if($beltReady) {
            foreach($beltResult in $beltResults){$script:beltRows+=$beltResult}
            if(@($beltResults | Where-Object {-not $_.passed}).Count){throw "Network phase $Phase failed; see its state snapshots"}
            if($Phase -eq 7 -and $beltResults.Count -eq 2) {
                $beltDistanceSquared=0.0
                foreach($beltAxis in 0..2){$beltDelta=[double]$beltResults[0].pickup_position[$beltAxis]-[double]$beltResults[1].pickup_position[$beltAxis];$beltDistanceSquared+=$beltDelta*$beltDelta}
                $script:beltLandingError=[Math]::Sqrt($beltDistanceSquared)
                if($script:beltLandingError -gt 5.0){throw "Authoritative and client pickup landing positions disagree by $script:beltLandingError cm"}
            }
            Write-Output "BELT_REVIEW_PHASE $Phase passed";return
        }
        foreach($beltPeer in $beltPeers){if($beltPeer.HasExited -and $beltPeer.ExitCode -ne 0){throw "Owned peer $($beltPeer.Id) exited $($beltPeer.ExitCode)"}}
        Start-Sleep -Seconds 2
    }
    throw "Network phase $Phase timed out"
}
try {
    # These are read-only game peers with separate profiles, port and registry
    # caches. Asset saves remain serialized by run_asset.ps1, independently.
    $beltMemory=Get-CimInstance Win32_OperatingSystem
    if($beltMemory.FreePhysicalMemory -lt 8MB -or $beltMemory.FreeVirtualMemory -lt 16MB){throw 'Insufficient available memory for the two isolated peers'}
    if(Get-NetUDPEndpoint -LocalPort $beltPort -ErrorAction SilentlyContinue){throw 'Test UDP port is occupied'}
    Set-BeltPhase 0
    $beltStarted=Start-BeltPeer 'host';$beltHost=$beltStarted[-1];$beltStarted | Where-Object {$_ -is [string]} | Write-Output
    Wait-BeltPhase 0 @('host')
    Set-BeltPhase 1
    $beltStarted=Start-BeltPeer 'client';$beltClient=$beltStarted[-1];$beltStarted | Where-Object {$_ -is [string]} | Write-Output
    foreach($beltPhase in 1..9){Set-BeltPhase $beltPhase;Wait-BeltPhase $beltPhase}
    Set-BeltPhase 10 'client'
    if(-not $beltClient.WaitForExit(30000)){throw 'Initial client did not close for reconnect'}
    Wait-BeltPhase 10 @('host')
    Set-BeltPhase 11
    $beltStarted=Start-BeltPeer 'client' -Rejoin;$beltStarted | Where-Object {$_ -is [string]} | Write-Output
    Wait-BeltPhase 11
    Set-BeltPhase 12;Wait-BeltPhase 12
    @{passed=$true;states=$beltRows;pickup_landing_error_cm=$script:beltLandingError;transport='real UDP loopback listen host and client';lag_ms_each_peer=60;loss_percent_each_peer=3;rendered=$false;production_profiles_modified=$false} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $beltReviewRoot 'summary.json') -Encoding UTF8
} catch {
    @{passed=$false;error=$_.Exception.Message;states=$beltRows;rendered=$false} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $beltReviewRoot 'summary.json') -Encoding UTF8
    Write-Output $_.Exception.Message
    $script:beltFailed=$true
} finally {
    Set-BeltPhase 99 'all'
    foreach($beltPeer in $beltPeers) {
        if(-not $beltPeer.HasExited){[void]$beltPeer.WaitForExit(10000)}
        if(-not $beltPeer.HasExited){$beltLive=Get-CimInstance Win32_Process -Filter "ProcessId=$($beltPeer.Id)";if($beltLive.CommandLine -like '*-TacticalBeltAudit*' -and $beltLive.CommandLine -like ('*'+$beltStamp+'*')){Stop-Process -Id $beltPeer.Id}}
    }
    Write-Output "BELT_REVIEW_OUTPUT $beltReviewRoot"
}
if($script:beltFailed){exit 1}
