param([string]$Attempt=(Get-Date -Format 'yyyyMMdd-HHmmss'))
$ErrorActionPreference='Stop'
$auditProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$auditRun=Join-Path $auditProject ('Saved/UnknownJoinDamage20261116/Wire-'+$Attempt)
$auditHost=Join-Path $auditRun 'Host'
$auditGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$auditHeld=$false
$auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
$auditPort=20826
function Start-AuditPeer([string]$Role,[string]$Map) {
    $peerDir=Join-Path $auditRun $Role
    New-Item -ItemType Directory -Force -Path $peerDir | Out-Null
    $peerArgs=@(('"'+$auditHost+'/FPSGAME.uproject"'),('"'+$Map+'"'),
        '-game','-nullrhi','-nosound','-unattended','-nosplash','-UnknownJoinAudit',
        '-SkipStartupMenu','-ClearwaterNoMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-ColdSteelProfile=UnknownJoin_'+$Attempt+'_'+$Role),('-port='+$auditPort),
        ('-UserDir="'+$peerDir+'"'),('-abslog="'+$peerDir+'/runtime.log"'),
        ('-UnknownJoinPeer='+$Role),'-UnknownJoinIdentity=EF358F601AB34D499AD93824B523B80F',('-UnknownJoinOutput="'+$auditRun+'"'),
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
        '-ExecCmds="t.MaxFPS 60,NetEmulation.PktLag 60,NetEmulation.PktLoss 2"',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $auditOwned.Add($peer)
    @{pid=$peer.Id;args=$peerArgs} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$peerDir/launch.json" -Encoding utf8
    Write-Output "UNKNOWN_JOIN_START role=$Role pid=$($peer.Id)"
    return $peer
}
function Wait-AuditMarker([string]$Marker,[Diagnostics.Process]$Peer,[int]$Seconds=300) {
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    while([DateTime]::UtcNow -lt $deadline) {
        if((Test-Path -LiteralPath "$auditRun/host/runtime.log") -and
            (Select-String -LiteralPath "$auditRun/host/runtime.log" -SimpleMatch $Marker -Quiet)){return}
        if($Peer.HasExited){throw "Host exited before $Marker"}
        Start-Sleep -Seconds 2
    }
    throw "Timeout waiting for $Marker"
}
try {
    try {$auditHeld=$auditGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$auditHeld=$true}
    if(-not $auditHeld){throw 'Shared UE batch still occupied; no peer started'}
    $buildDeadline=[DateTime]::UtcNow.AddMinutes(10)
    while(@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')) -and $_.CommandLine -notmatch '\bFPSGAME\s+Win64\s+Development\b'
    }).Count){
        if([DateTime]::UtcNow -gt $buildDeadline){throw 'Preserve in-progress module build; no peer started'}
        Start-Sleep -Seconds 3
    }
    if(Test-Path -LiteralPath $auditRun){throw "Run already exists: $auditRun"}
    if(Get-NetUDPEndpoint -LocalPort $auditPort -ErrorAction SilentlyContinue){throw 'Audit UDP port already occupied'}
    $auditMemory=Get-CimInstance Win32_OperatingSystem
    if($auditMemory.FreePhysicalMemory/1MB -lt 8 -or $auditMemory.FreeVirtualMemory/1MB -lt 14){throw 'Insufficient headroom for two NullRHI peers'}
    New-Item -ItemType Directory -Force -Path "$auditHost/Binaries/Win64" | Out-Null
    Copy-Item -LiteralPath "$auditProject/FPSGAME.uproject" -Destination "$auditHost/FPSGAME.uproject"
    Copy-Item -LiteralPath "$auditProject/Config" -Destination "$auditHost/Config" -Recurse
    foreach($folder in @('Content','Plugins','Shaders')){
        if(Test-Path -LiteralPath "$auditProject/$folder"){
            New-Item -ItemType Junction -Path "$auditHost/$folder" -Target "$auditProject/$folder" | Out-Null
        }
    }
    foreach($file in @('UnrealEditor-FPSGAME.dll','UnrealEditor.modules')){
        Copy-Item -LiteralPath "$auditProject/Binaries/Win64/$file" -Destination "$auditHost/Binaries/Win64/$file"
    }
    $launch=Start-AuditPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.UnknownJoinAuditGameMode?listen'
    $hostPeer=$launch[-1]; $launch | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'UNKNOWN_JOIN_HOST_READY' $hostPeer
    Start-Sleep -Seconds 8
    $phase=0
    foreach($role in @('first','rejoin','expired')) {
        $launch=Start-AuditPeer $role ('127.0.0.1:'+$auditPort)
        $launch | Where-Object {$_ -is [string]} | Write-Output
        $phase++
        Wait-AuditMarker ('UNKNOWN_JOIN_DISCONNECTED phase='+$phase) $hostPeer 420
    }
    Wait-AuditMarker 'UNKNOWN_JOIN_RESULT' $hostPeer 30
    foreach($peer in $auditOwned){[void]$peer.WaitForExit(10000)}
    $hostResult=Get-Content -LiteralPath "$auditRun/host.json" -Raw | ConvertFrom-Json
    $passed=$hostResult.passed
    $counts=@{host=$hostResult.cases.Count}
    foreach($role in @('first','rejoin','expired')){
        $result=Get-Content -LiteralPath "$auditRun/$role.json" -Raw | ConvertFrom-Json
        $passed=$passed -and $result.passed
        $counts[$role]=$result.cases.Count
    }
    $passed=$passed -and $counts.first -eq 17 -and $counts.rejoin -eq 1 -and $counts.expired -eq 2
    @{passed=$passed;cases=$counts;real_connections=3;fresh_guest_processes=3;
        dll_sha256=(Get-FileHash -LiteralPath "$auditHost/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;
        requested_lag_ms_each_peer=60;requested_loss_percent_each_peer=2;rendered=$false;run=$auditRun} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$auditRun/summary.json" -Encoding utf8
    Write-Output "UNKNOWN_JOIN_DONE passed=$passed run=$auditRun"
    if(-not $passed){exit 1}
} finally {
    foreach($peer in $auditOwned){
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($auditHost) -and $live.CommandLine.Contains('-UnknownJoinAudit')){
                Stop-Process -Id $peer.Id
                [void]$peer.WaitForExit(10000)
            }
        }
    }
    if($auditHeld){$auditGate.ReleaseMutex()};$auditGate.Dispose()
}
