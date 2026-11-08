param([string]$ProjectRoot='D:/FPS3D/FPSGAME',[switch]$ConversationOnly)
$ErrorActionPreference='Stop'
$project=$ProjectRoot
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$out=Join-Path $PSScriptRoot ('Native/'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force -Path $out | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no commandlet started.'}
    if(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    $oldHaste="$project/Saved/LightningHasteReview20261107/native-result.json"
    if(Test-Path -LiteralPath $oldHaste){Copy-Item -LiteralPath $oldHaste -Destination "$out/haste-before.json"}
    $tasks=@(
        @{name='conversation';run='SkillNetworkAudit';flag='-ConversationCombatOnly'},
        @{name='lightning-haste';run='SkillNetworkAudit';flag='-LightningHasteOnly'},
        @{name='flame-armor';run='SkillNetworkAudit';flag='-FlameArmorOnly'},
        @{name='flame-armor-stats';run='SkillNetworkAudit';flag='-FlameArmorStatsOnly'},
        @{name='star-marrow-motion';run='RuneSwordAudit';flag='-StarMarrowMotionOnly'}
    )
    if($ConversationOnly){$tasks=@($tasks | Where-Object {$_.name -eq 'conversation'})}
    $receipts=@()
    foreach($t in $tasks){
        $name=$t.name
        $args=@("$project/FPSGAME.uproject",('-run='+$t.run),$t.flag,"-Output=$out/$name.json","-Report=$out/$name.txt",'-unattended','-nop4','-nosplash','-nosound','-nullrhi','-Multiprocess','-NoLiveCoding',
          '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False',"-abslog=$out/$name.log")
        & $exe @args *> "$out/$name.console.log"
        $code=$LASTEXITCODE
        if($name -eq 'lightning-haste' -and (Test-Path -LiteralPath $oldHaste)){Copy-Item -LiteralPath $oldHaste -Destination "$out/$name.json"}
        $receipts+=@{name=$name;exit_code=$code}
        Write-Output "NATIVE_FINISHED $name exit=$code"
    }
    $receipts | ConvertTo-Json | Set-Content -LiteralPath "$out/receipt.json" -Encoding utf8
    Write-Output "NATIVE_RESULTS $out"
    if(@($receipts | Where-Object {$_.exit_code -ne 0}).Count){exit 1}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
