param([string]$Only='')
$ErrorActionPreference='Stop';$env:UE_SKIP_UBT_SDK_SETUP='1'
$taskRoot='D:/FPS3D/ThunderHammerFullReviewHost20261102'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.ThreadCount -gt 0}){throw 'Another commandlet is active.'}
    $cases=@(
      @{name='jilei-intent';run='WarhammerModificationAudit';extra='-JiLeiIntent'},
      @{name='heavy-formula';run='WarhammerModificationAudit';extra='-HeavyFormula'},
      @{name='thor-assets-mods';run='WarhammerModificationAudit';extra='-Definition=ue_thunder_god_hammer'},
      @{name='zhenting';run='WarhammerModificationAudit';extra='-ZhenTing'},
      @{name='recall';run='ThunderHammerRecallAudit';extra=''},
      @{name='switch';run='ThunderHammerRecallAudit';extra='-WeaponSwitchOnly'},
      @{name='preview';run='ThunderHammerRecallAudit';extra='-PreviewOnly'},
      @{name='storm-lifecycle';run='WarhammerModificationAudit';extra='-StormDriveLifecycle'},
      @{name='profile-receipts';run='ColdSteelAcquisitionAudit';extra="-AcquisitionAuditRoot=$PSScriptRoot/ProfileReceipts"})
    $results=@()
    if(Test-Path -LiteralPath "$PSScriptRoot/native-receipts.json"){
        $loaded=Get-Content "$PSScriptRoot/native-receipts.json" -Raw | ConvertFrom-Json
        $results=@(foreach($entry in $loaded){if($entry.case){$entry}elseif($entry.value){$entry.value}})
    }
    foreach($case in $cases){
        if($Only -and $Only.Split(',') -notcontains $case.name){continue}
        if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 3MB){throw 'Less than 3 GiB available; remaining native cases preserved for later.'}
        $name=$case.name
        $userRoot=if($name -eq 'profile-receipts'){"$PSScriptRoot/ProfileReceipts"}else{"$PSScriptRoot/NativeUser"}
        New-Item -ItemType Directory -Path $userRoot -Force | Out-Null
        $args=@("$taskRoot/FPSGAME.uproject",('-run='+$case.run),"-Out=$PSScriptRoot/$name.json",'-unattended','-nop4','-nosplash','-NoSound','-NoLiveCoding','-NullRHI','-NoShaderCompile',"-abslog=$PSScriptRoot/$name.log","-UserDir=$PSScriptRoot/NativeUser/",'-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False')
        if($case.extra){$args+=$case.extra}
        $args=@($args | ForEach-Object {if($_ -like '-UserDir=*'){"-UserDir=$userRoot/"}else{$_}})
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @args *> "$PSScriptRoot/$name-console.log"
        $code=$LASTEXITCODE;$results=@($results|Where-Object {$_.case -ne $name});$results+=@{case=$name;exit_code=$code};Write-Output "$name exit=$code"
        ConvertTo-Json -InputObject @($results) -Depth 6 | Set-Content "$PSScriptRoot/native-receipts.json" -Encoding utf8
    }
    if(@($results|Where-Object {$_.exit_code -ne 0}).Count){exit 1}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
