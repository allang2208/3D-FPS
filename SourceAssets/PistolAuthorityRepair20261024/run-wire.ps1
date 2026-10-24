param([string]$Name=('wire-'+(Get-Date -Format 'yyyyMMdd-HHmmss')),[string]$Project='D:/FPS3D/FPSGAME/SourceAssets/PistolRepair20261022/RuntimeBuilt28/FPSGAME.uproject',[switch]$ReadOnlySnapshot=$true)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath "$PSScriptRoot/$Name-cancelled.json") {Write-Output "SUPERSEDED_WIRE_SKIPPED $Name";return}
$pistolWireDir=Join-Path $PSScriptRoot $Name
if(Test-Path -LiteralPath $pistolWireDir){throw 'Use a new evidence directory.'}
New-Item -ItemType Directory -Path $pistolWireDir | Out-Null
$pistolWirePort=19927
if(Get-NetUDPEndpoint -LocalPort $pistolWirePort -ErrorAction SilentlyContinue){throw 'Pistol audit UDP port occupied.'}
if($ReadOnlySnapshot -and ([IO.Path]::GetFullPath((Split-Path -Parent (Split-Path -Parent $Project))) -ne [IO.Path]::GetFullPath('D:/FPS3D/FPSGAME/SourceAssets/PistolRepair20261022') -or (Split-Path -Leaf (Split-Path -Parent $Project)) -notmatch '^RuntimeBuilt\d+$')){throw 'The parallel read-only exception is limited to the copied runtime.'}
$pistolWireGateName=if($ReadOnlySnapshot){'Local\CodexPistolReadOnly20261022'}else{'Local\CodexUeMcp-Port-8000'}
$pistolWireGate=[Threading.Mutex]::new($false,$pistolWireGateName)
$pistolWireHeld=$false
$pistolWireOwned=[System.Collections.Generic.List[System.Diagnostics.Process]]::new()
function Start-PistolPeer([string]$role,[string]$map) {
    $pistolPeerArgs=@(('"'+$Project+'"'),('"'+$map+'"'),'-game','-nullrhi','-nosound','-unattended','-nosplash',
        '-ShotgunWireAudit','-PistolAmmoWire',
        '-DDC=(EnginePak=InstalledEnginePak,WarmRead=(Type=FileSystem,Path=D:/FPS3D/DerivedDataCache,ReadOnly=true,DeleteUnused=false,PromptIfMissing=false),Local=(Type=FileSystem,Path=D:/FPS3D/FPSGAME/SourceAssets/PistolRepair20261022/DDC,DeleteUnused=false,PromptIfMissing=false))','-ini:Engine:[/Script/Engine.PhysicsSettings]:DefaultGravityZ=0.0',
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        ('-ColdSteelProfile=ShotgunWireAudit_Pistol_'+$Name+'_'+$role),('-port='+$pistolWirePort),
        ('-UserDir="'+$pistolWireDir+'/'+$role+'/"'),('-ShotgunWireOutput="'+$pistolWireDir+'/'+$role+'.json"'),
        ('-abslog="'+$pistolWireDir+'/'+$role+'.log"'),'-ExecCmds="fps.body.WorldBodySuppress 1,t.MaxFPS 30"')
    $pistolPeer=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $pistolPeerArgs -Environment @{UE_SKIP_UBT_SDK_SETUP='1'} -WindowStyle Hidden -PassThru
    $pistolWireOwned.Add($pistolPeer)
    @{role=$role;pid=$pistolPeer.Id;arguments=$pistolPeerArgs;started=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath ($pistolWireDir+'/'+$role+'-launch.json') -Encoding utf8
    Write-Output "PISTOL_WIRE_PEER $role PID=$($pistolPeer.Id)"
    return $pistolPeer
}
function Wait-PistolMarker([string]$marker,[System.Diagnostics.Process]$hostPeer,[int]$minutes=12) {
    $pistolMarkerDeadline=(Get-Date).AddMinutes($minutes)
    while((Get-Date) -lt $pistolMarkerDeadline) {
        if((Test-Path -LiteralPath "$pistolWireDir/host.log") -and (Select-String -LiteralPath "$pistolWireDir/host.log" -SimpleMatch $marker -Quiet)){return}
        if($hostPeer.HasExited){throw "Audit host exited before $marker"}
        Start-Sleep -Seconds 1
    }
    throw "Timed out waiting for $marker"
}
try {
    Write-Output 'Waiting for the shared UE batch and runtime capacity.'
    try {$pistolWireHeld=$pistolWireGate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$pistolWireHeld=$true}
    if(-not $pistolWireHeld){throw 'Shared UE batch remained occupied.'}
    $pistolWireDeadline=(Get-Date).AddMinutes(20)
    do {
        $pistolWireBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -in @('UnrealEditor-Cmd.exe','UnrealEditor.exe') -or (-not $ReadOnlySnapshot -and $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool|AutomationTool')) -and $_.CommandLine -like '*FPSGAME*'
        })
        # The user authorized this copied, read-only runtime while formal work
        # continues. Unrelated headless asset imports do not load/save its test
        # profiles or pistol assets; capacity still gates both peers together.
        if($ReadOnlySnapshot){$pistolWireBusy=@()}
        $pistolWireMemory=Get-CimInstance Win32_OperatingSystem
        if(-not $pistolWireBusy.Count -and $pistolWireMemory.FreePhysicalMemory -gt 8GB/1KB -and $pistolWireMemory.FreeVirtualMemory -gt 16GB/1KB){break}
        if((Get-Date) -gt $pistolWireDeadline){throw 'No free window for two isolated network peers.'}
        Start-Sleep -Seconds 5
    } while($true)
    $pistolHostOutput=Start-PistolPeer 'host' '/Engine/Maps/Entry?game=/Script/FPSGAME.ShotgunWireAuditGameMode?listen'
    $pistolHost=$pistolHostOutput[-1];$pistolHostOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-PistolMarker 'SHOTGUN_WIRE_HOST_READY' $pistolHost 5
    Wait-PistolMarker 'seconds to LoadMap(/Engine/Maps/Entry)' $pistolHost 5
    $pistolClientOutput=Start-PistolPeer 'client' ('127.0.0.1:'+$pistolWirePort)
    $pistolClient=$pistolClientOutput[-1];$pistolClientOutput | Where-Object {$_ -is [string]} | Write-Output
    Wait-PistolMarker 'SHOTGUN_WIRE_RESULT' $pistolHost 30
    $pistolWireResult=Get-Content -LiteralPath "$pistolWireDir/host.json" -Raw | ConvertFrom-Json
    @{passed=$pistolWireResult.passed;cases=$pistolWireResult.cases.Count;transport='real local UDP listen host + client; production reload and fire executors';port=$pistolWirePort;lag_ms_each_peer=60;loss_percent_each_peer=5;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$pistolWireDir/receipt.json" -Encoding utf8
    Write-Output "PISTOL_WIRE_FINISHED PASS=$($pistolWireResult.passed)"
    if(-not $pistolWireResult.passed){exit 1}
} finally {
    foreach($pistolPeer in $pistolWireOwned) {
        if(-not $pistolPeer.HasExited){[void]$pistolPeer.WaitForExit(5000)}
        if(-not $pistolPeer.HasExited) {
            $pistolLive=Get-CimInstance Win32_Process -Filter "ProcessId=$($pistolPeer.Id)"
            if($pistolLive.Name -eq 'UnrealEditor-Cmd.exe' -and $pistolLive.CommandLine -like '*-PistolAmmoWire*' -and $pistolLive.CommandLine -like ('*'+$pistolWireDir+'*')){Stop-Process -Id $pistolPeer.Id}
        }
    }
    if($pistolWireHeld){$pistolWireGate.ReleaseMutex()};$pistolWireGate.Dispose()
}
