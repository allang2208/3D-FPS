param([switch]$SkipBuild,[string]$Only='',[switch]$RepairSeatTangents)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    for($attempt=0;$attempt -lt 20 -and -not $taskHeld;$attempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
        if(-not $taskHeld){Write-Output 'Waiting for existing UE batch.'}
    }
    if(-not $taskHeld){throw 'UE batch occupied; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE processes preserved.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Existing build preserved.'}
    if(-not $SkipBuild) {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE *> (Join-Path $PSScriptRoot 'build.log')
        $code=$LASTEXITCODE
        @{exit_code=$code;target='FPSGAMEEditor Win64 Development'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
        Write-Output "Build exit=$code"
        if($code -ne 0){Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build.log') -Tail 65;exit $code}
    }
    if($RepairSeatTangents) {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/repair_seat_tangents.py" -unattended -nop4 -nosplash -NoSound -NoLiveCoding -AllowCommandletRendering -RenderOffscreen -d3d12 -sm6 "-abslog=$PSScriptRoot/seat-tangents.log" *> (Join-Path $PSScriptRoot 'seat-tangents-console.log')
        if($LASTEXITCODE -ne 0){throw 'Seat tangent save failed.'}
    }
    $cases=@(
        @{name='jilei-intent';run='WarhammerModificationAudit';extra='-JiLeiIntent'},
        @{name='heavy-formula';run='WarhammerModificationAudit';extra='-HeavyFormula'},
        @{name='thor-assets-mods';run='WarhammerModificationAudit';extra='-Definition=ue_thunder_god_hammer'},
        @{name='zhenting';run='WarhammerModificationAudit';extra='-ZhenTing'},
        @{name='recall';run='ThunderHammerRecallAudit';extra=''},
        @{name='switch';run='ThunderHammerRecallAudit';extra='-WeaponSwitchOnly'},
        @{name='preview';run='ThunderHammerRecallAudit';extra='-PreviewOnly'},
        @{name='storm-lifecycle';run='WarhammerModificationAudit';extra='-StormDriveLifecycle'}
    )
    $results=@()
    foreach($case in $cases){
        if($Only -and $Only.Split(',') -notcontains $case.name){continue}
        $name=$case.name
        $args=@("$taskRoot/FPSGAME.uproject",('-run='+$case.run),"-Out=$PSScriptRoot/$name.json",'-unattended','-nop4','-nosplash','-NoSound','-NoLiveCoding','-NullRHI',"-abslog=$PSScriptRoot/$name.log")
        if($case.extra){$args+=$case.extra}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @args *> (Join-Path $PSScriptRoot ($name+'-console.log'))
        $code=$LASTEXITCODE;$results+=@{case=$name;exit_code=$code};Write-Output "$name exit=$code"
    }
    $results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'native-receipts.json') -Encoding utf8
    if(@($results|Where-Object {$_.exit_code -ne 0}).Count){exit 1}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
