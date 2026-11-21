// Tools/WorldGeneration/Run-VillageNetworkAudit.ps1
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 3-5 | file scope
    [string]$Build,
    [switch]$Construction,
    [ValidateRange(1024,65535)][int]$Port=20318

// Lines 11-11 | $auditProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$auditPort=$Port

// Lines 19-19 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    $peerArgs=@(('"'+$auditHost+'/FPSGAME.uproject"'),('"'+$Map+'"'),'-game','-nullrhi','-NoShaderCompile','-NoLiveCoding','-nosound','-unattended','-nosplash',

// Lines 30-30 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    if($Construction){$peerArgs+='-VillageConstructionAudit'}

// Lines 38-38 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
function Wait-AuditMarker([string]$Marker,[Diagnostics.Process]$Peer,[int]$Seconds=1500,[Diagnostics.Process]$Guest) {

// Lines 44-44 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
        if($Guest -and $Guest.HasExited){throw "Guest exited before $Marker (code $($Guest.ExitCode))"}

// Lines 59-68 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    if ($Build) {
        foreach($target in 'FPSGAMEEditor','FPSGAME') {
            $receipt=Get-Content -LiteralPath "$Build/$target-build.json" -Raw | ConvertFrom-Json
            if($receipt.exit_code -ne 0){throw "$target build failed"}
        }
        $sourceReceipt=Get-Content -LiteralPath "$Build/sources.json" -Raw | ConvertFrom-Json
        foreach($source in $sourceReceipt.files) {
            if((Get-FileHash -LiteralPath (Join-Path $auditProject $source.path)).Hash -ne $source.sha256) {
                throw "Source changed after build input snapshot: $($source.path)"
            }

// Lines 76-87 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    foreach($folder in 'Content','Shaders') {New-Item -ItemType Junction -Path "$auditHost/$folder" -Target "$auditProject/$folder" | Out-Null}
    # A headless peer must not hold the project's networking DLL open during other builds.
    New-Item -ItemType Directory -Path "$auditHost/Plugins/ColdSteelNet/Binaries/Win64" -Force | Out-Null
    foreach($plugin in Get-ChildItem -LiteralPath "$auditProject/Plugins" -Directory) {
        if($plugin.Name -ne 'ColdSteelNet') {
            New-Item -ItemType Junction -Path "$auditHost/Plugins/$($plugin.Name)" -Target $plugin.FullName | Out-Null
        }
    }
    Copy-Item -LiteralPath "$auditProject/Plugins/ColdSteelNet/ColdSteelNet.uplugin" -Destination "$auditHost/Plugins/ColdSteelNet"
    foreach($file in 'UnrealEditor-ColdSteelNet.dll','UnrealEditor.modules') {
        Copy-Item -LiteralPath "$auditProject/Plugins/ColdSteelNet/Binaries/Win64/$file" -Destination "$auditHost/Plugins/ColdSteelNet/Binaries/Win64"
    }

// Lines 92-97 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    $manifest='UnrealEditor.modules'
    Copy-Item -LiteralPath "$auditProject/Binaries/Win64/$manifest" -Destination "$auditHost/Binaries/Win64/$manifest"
    $moduleMap=Get-Content -LiteralPath "$auditHost/Binaries/Win64/$manifest" -Raw | ConvertFrom-Json
    foreach ($entry in $moduleMap.Modules.PSObject.Properties) {
        Copy-Item -LiteralPath (Join-Path "$auditProject/Binaries/Win64" $entry.Value) -Destination "$auditHost/Binaries/Win64"
    }

// Lines 104-106 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    Wait-AuditMarker "IpNetDriver listening on port $auditPort" $hostPeer
    $auditMutex.ReleaseMutex()
    $auditHeld=$false

// Lines 108-108 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    Wait-AuditMarker 'VILLAGE_NET_DISCONNECT_CLIENT' $hostPeer -Guest $guestPeer

// Lines 125-126 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    $initial=if($Construction){@($r.checks | Where-Object {$_.case -eq 'same_guest_reconnects_with_upgrades_and_paid_bay' -and $_.passed}).Count -eq 1}
        else{Select-String -LiteralPath "$auditRun/rejoin.log" -Pattern 'VILLAGE_NET_GATE_INITIAL id=10000 angle=88.00 left=88.00 right=-88.00' -Quiet}

// Lines 129-131 | $auditOwned=[Collections.Generic.List[Diagnostics.Process]]::new()
    $summary=@{passed=$passed;cases=$r.checks.Count;clean_exit=$clean;source_world_unchanged=$unchanged;module_sha256=$moduleHash;real_udp=$true;rendered=$false}
    if($Construction){$summary.late_join_construction_state=$initial}else{$summary.late_join_initial_pose=$initial}
    $summary|ConvertTo-Json|Set-Content -LiteralPath "$auditRun/summary.json"
