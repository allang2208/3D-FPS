param([string]$Only='')
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$out=Join-Path $PSScriptRoot ('Native/'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $out | Out-Null
$tasks=@(
    @{name='session';run='SkillNetworkAudit';flags=@('-SessionSkillsOnly')},
    @{name='leap-ballistic';run='LeapStrikeAudit';flags=@('-BallisticOnly')},
    @{name='leap-control';run='LeapStrikeAudit';flags=@('-ControlOnly')},
    @{name='leap-landing';run='LeapStrikeAudit';flags=@('-LandingOnly')},
    @{name='leap-camera';run='LeapStrikeAudit';flags=@('-CameraOnly')},
    @{name='arrow-rain-audio';run='BowSkillTrainingAudit';flags=@('-MagicArrowRain','-ArrowRainAudioOnly')},
    @{name='bow-network';run='BowSkillTrainingAudit';flags=@('-BowNetworkReview')},
    @{name='elemental-hold';run='BowSkillTrainingAudit';flags=@('-ElementalHoldReview')},
    @{name='flame-armor';run='SkillNetworkAudit';flags=@('-FlameArmorOnly')},
    @{name='flame-armor-stats';run='SkillNetworkAudit';flags=@('-FlameArmorStatsOnly')},
    @{name='warhammer-network';run='WarhammerNetworkAudit';flags=@()},
    @{name='quick-variants';run='SkillNetworkAudit';flags=@('-ConversationCombatOnly')},
    @{name='star-marrow-motion';run='RuneSwordAudit';flags=@('-StarMarrowMotionOnly')}
)
if($Only){$tasks=@($tasks | Where-Object {$_.name -in $Only.Split(',')})}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no commandlet started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    $receipts=@()
    foreach($t in $tasks){
        $dir=Join-Path $out $t.name;New-Item -ItemType Directory -Force -Path $dir | Out-Null
        $outArg=if($t.run -eq 'WarhammerNetworkAudit'){"-Out=$dir/result.json"}else{"-Out=$dir"}
        $args=@("$project/FPSGAME.uproject",('-run='+$t.run))+@($t.flags)+@("-Output=$dir/result.json",$outArg,"-ReportDir=$dir","-Report=$dir/report.txt",'-unattended','-nop4','-nosplash','-nosound','-nullrhi','-Multiprocess','-NoLiveCoding',
            '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',"-abslog=$dir/engine.log")
        & $exe @args *> "$dir/console.log"
        $code=$LASTEXITCODE;$receipts+=@{name=$t.name;exit_code=$code;directory=$dir}
        $receipts | ConvertTo-Json | Set-Content -LiteralPath "$out/receipt.json" -Encoding utf8
        Write-Output "NATIVE_FINISHED $($t.name) exit=$code path=$dir"
    }
    if(@($receipts | Where-Object {$_.exit_code -ne 0}).Count){exit 1}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
