param([string]$Attempt=(Get-Date -Format 'yyyyMMdd-HHmmss'))
$ErrorActionPreference='Stop'
$auditProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$auditRun=Join-Path $auditProject ('Saved/UnknownNetworkReview20261116/Wire-'+$Attempt)
$auditHost=Join-Path $auditRun 'Host'
$auditGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$auditHeld=$false
$auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
$auditPort=20816
function Start-AuditPeer([string]$Role,[string]$Map) {
    $peerDir=Join-Path $auditRun $Role
    New-Item -ItemType Directory -Force -Path $peerDir | Out-Null
    $peerArgs=@(('"'+$auditHost+'/FPSGAME.uproject"'),('"'+$Map+'"'),
        '-game','-nullrhi','-nosound','-unattended','-nosplash','-UnknownNetworkAudit',
        '-SkipStartupMenu','-ClearwaterNoMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-ColdSteelProfile=UnknownNetwork_'+$Attempt+'_'+$Role),('-port='+$auditPort),
        ('-UserDir="'+$peerDir+'"'),('-abslog="'+$peerDir+'/runtime.log"'),
        ('-UnknownNetworkOutput="'+$auditRun+'"'),
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
        '-ExecCmds="t.MaxFPS 60,NetEmulation.PktLag 60,NetEmulation.PktLoss 2"',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $peer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $peerArgs -WindowStyle Hidden -PassThru
    $auditOwned.Add($peer)
    @{pid=$peer.Id;args=$peerArgs} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$peerDir/launch.json" -Encoding utf8
    Write-Output "UNKNOWN_WIRE_START role=$Role pid=$($peer.Id)"
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
        $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
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
    $launch=Start-AuditPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.UnknownNetworkAuditGameMode?listen'
    $hostPeer=$launch[-1]; $launch | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'UNKNOWN_WIRE_HOST_READY' $hostPeer
    $launch=Start-AuditPeer 'client' ('127.0.0.1:'+$auditPort)
    $clientPeer=$launch[-1]; $launch | Where-Object {$_ -is [string]} | Write-Output
    Wait-AuditMarker 'UNKNOWN_WIRE_RESULT role=host' $hostPeer 720
    foreach($peer in $auditOwned){[void]$peer.WaitForExit(10000)}
    $hostResult=Get-Content -LiteralPath "$auditRun/host.json" -Raw | ConvertFrom-Json
    $clientResult=Get-Content -LiteralPath "$auditRun/client.json" -Raw | ConvertFrom-Json
    $passed=$hostResult.passed -and $clientResult.passed -and $hostResult.cases.Count -eq 74 -and $clientResult.cases.Count -eq 74
    @{passed=$passed;host_cases=$hostResult.cases.Count;client_cases=$clientResult.cases.Count;
        dll_sha256=(Get-FileHash -LiteralPath "$auditHost/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;
        requested_lag_ms_each_peer=60;requested_loss_percent_each_peer=2;rendered=$false;run=$auditRun} |
        ConvertTo-Json | Set-Content -LiteralPath "$auditRun/summary.json" -Encoding utf8
    Write-Output "UNKNOWN_WIRE_DONE passed=$passed run=$auditRun"
    if(-not $passed){exit 1}
} finally {
    foreach($peer in $auditOwned){
        if(-not $peer.HasExited){
            $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
            if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($auditHost) -and $live.CommandLine.Contains('-UnknownNetworkAudit')){
                Stop-Process -Id $peer.Id
                [void]$peer.WaitForExit(10000)
            }
        }
    }
    if($auditHeld){$auditGate.ReleaseMutex()};$auditGate.Dispose()
}
