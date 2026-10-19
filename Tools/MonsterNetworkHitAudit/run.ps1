param([ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='authority', [switch]$SkipBuild)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/SourceAssets/MonsterNetworkHitAudit20261018"
New-Item -ItemType Directory -Force -Path "$taskOut/Logs" | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(60))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; network audit not started.'}
    Write-Output 'Network hit audit batch acquired.'
    if(-not $SkipBuild){
        $env:MONSTER_AUDIT_OUTPUT=$taskOut
        try{& "$taskRoot/Tools/NonHumanoidHitAudit/build_native.ps1" -Targets FPSGAMEEditor,FPSGAME -MaximumWaitSeconds 1200 -MaxParallelActions 6 -UseDefaultLiveCodingSupport}
        finally{Remove-Item Env:MONSTER_AUDIT_OUTPUT -ErrorAction SilentlyContinue}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=MonsterNetworkHitAudit "-Report=$taskOut/$Label.json" -unattended -nop4 -nosplash -nullrhi -nosound -NoLiveCoding "-abslog=$taskOut/Logs/$Label.log" *> "$taskOut/Logs/$Label-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;report="$taskOut/$Label.json";map_begin_play=$false;socket_transport=$false;assets_saved=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOut/$($Label)_exit.json" -Encoding utf8
    if($taskExit -ne 0){throw "Network audit exit $taskExit; evidence retained."}
    Write-Output "Network authority audit complete: $Label"
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
