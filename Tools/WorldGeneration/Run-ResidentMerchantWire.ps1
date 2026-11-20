param([ValidateRange(19480,19489)][int]$Port=19483,[string]$Module)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../..").Path
$run=Join-Path $project ('Saved/ResidentMerchantWire/'+(Get-Date -Format 'yyyyMMdd-HHmmss-ffff'))
$stage=Join-Path $run 'Stage'
$evidence=Join-Path $run 'Evidence'
$engine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$owned=[Collections.Generic.List[Diagnostics.Process]]::new()
function Launch([string]$Role,[string]$Destination) {
    $user=if($Role -eq 'host'){'host'}else{'guest'}
    $userDir=Join-Path $run $user
    [void](New-Item -Force -ItemType Directory -Path $userDir)
    $options=@(('"'+$stage+'/FPSGAME.uproject"'),('"'+$Destination+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash','-NoLiveCoding',
        '-ResidentMerchantWire','-SkipStartupMenu','-ClearwaterNoMenu','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        ('-port='+$Port),('-ColdSteelProfile=ResidentWire_'+$user),('-UserDir="'+$userDir+'"'),('-abslog="'+$run+'/'+$Role+'.log"'),
        ('-MerchantEvidence="'+$evidence+'"'),('-MerchantRole='+$Role),
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
        '-ExecCmds="t.MaxFPS 35,NetEmulation.PktLag 45,NetEmulation.PktLoss 2,fps.Test.ResidentMerchantWire"',
        '-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:ConnectionTimeout=120.0',
        '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:InitialConnectTimeout=180.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $peer=Start-Process -FilePath $engine -ArgumentList $options -WindowStyle Hidden -PassThru
    $null=$peer.Handle
    $owned.Add($peer)
    Write-Host "RESIDENT_WIRE_START role=$Role pid=$($peer.Id)"
    return $peer
}
function Await([string]$Marker,[Diagnostics.Process]$Peer,[int]$Seconds=400){
    $deadline=[DateTime]::UtcNow.AddSeconds($Seconds)
    while(-not (Test-Path -LiteralPath (Join-Path $evidence $Marker))){
        $bad=Get-ChildItem -LiteralPath $evidence -Filter '*.failed' -File | Select-Object -First 1
        if($bad){throw "$($bad.Name) $(Get-Content -Raw -LiteralPath $bad.FullName)"}
        if($Peer.HasExited -or [DateTime]::UtcNow -ge $deadline){throw "Missing milestone $Marker, exited=$($Peer.HasExited)"}
        Start-Sleep -Seconds 2
    }
}
function Await-Exit([Diagnostics.Process]$Peer) {
    if(-not $Peer.WaitForExit(30000) -or $Peer.ExitCode -ne 0){throw "Unclean process exit $($Peer.Id)"}
}
if(Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue){throw "UDP port $Port is occupied"}
[void](New-Item -Force -ItemType Directory -Path "$stage/Binaries/Win64",$evidence)
Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$stage/FPSGAME.uproject"
Copy-Item -LiteralPath "$project/Config" -Destination "$stage/Config" -Recurse
foreach($folder in 'Content','Plugins','Shaders'){[void](New-Item -ItemType Junction -Path "$stage/$folder" -Target "$project/$folder")}
if (-not $Module){$Module="$project/Binaries/Win64/UnrealEditor-FPSGAME.dll"}
Copy-Item -LiteralPath $Module -Destination "$stage/Binaries/Win64/UnrealEditor-FPSGAME.dll"
Copy-Item -LiteralPath "$project/Binaries/Win64/UnrealEditor.modules" -Destination "$stage/Binaries/Win64/UnrealEditor.modules"
$report=[ordered]@{passed=$false;port=$Port;module=$Module;module_sha256=(Get-FileHash "$stage/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;map='/Engine/Maps/Entry';roles=@('host','guest','rejoin');events=@()}
Write-Host "RESIDENT_WIRE_RUN $run"
try {
    $entry='/Engine/Maps/Entry?game=/Script/FPSGAME.FPSGAMEGameMode'
    $hostPeer=Launch 'host' ($entry+'?listen')
    Await 'host.seed' $hostPeer
    $guest=Launch 'guest' ('127.0.0.1:'+$Port)
    Await 'guest.done' $guest
    Await-Exit $guest
    Await 'host.disconnected' $hostPeer
    $returning=Launch 'rejoin' ('127.0.0.1:'+$Port)
    Await 'host.done' $hostPeer
    Await-Exit $hostPeer
    Await-Exit $returning
    if((Get-Content -LiteralPath "$evidence/host.transport" -Raw).Trim() -ne 'lag=45 loss=2'){
        throw 'The listen server did not report the selected UDP packet simulation settings'
    }
    $report.passed=$true
} catch {
    $report['error']=$_.Exception.Message
    Write-Host "RESIDENT_WIRE_FAILURE $($report.error)"
} finally {
    foreach ($peer in $owned){
        if($peer.HasExited){continue}
        $live=Get-CimInstance Win32_Process -Filter "ProcessId=$($peer.Id)"
        if($live.Name -eq 'UnrealEditor-Cmd.exe' -and $live.CommandLine.Contains($stage) -and $live.CommandLine.Contains('-ResidentMerchantWire')){Stop-Process -Id $peer.Id -ErrorAction SilentlyContinue}
    }
    $report.events=@(Get-ChildItem -LiteralPath $evidence -File | Where-Object Extension -ne '.tmp' | Sort-Object Name | ForEach-Object {[ordered]@{name=$_.Name;text=(Get-Content -LiteralPath $_.FullName -Raw -Encoding utf8)}})
    $report|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$run/summary.json" -Encoding utf8
}
Write-Output "RESIDENT_WIRE_DONE passed=$($report.passed) receipt=$run/summary.json"
if(-not $report.passed){exit 1}
