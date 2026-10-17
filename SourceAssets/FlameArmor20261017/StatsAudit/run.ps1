$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    while(-not $held) {
        try{$held=$gate.WaitOne(60000)}catch [Threading.AbandonedMutexException]{$held=$true}
        if(-not $held){Write-Output 'Waiting for existing MCP batch'}
    }
    $exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    & $exe 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=SkillNetworkAudit -FlameArmorStatsOnly ('-Output='+$PSScriptRoot+'/stats.json') -unattended -nullrhi -Multiprocess -NoAutoSDK -nosound -NoLiveCoding ('-abslog='+$PSScriptRoot+'/stats.log') *> ($PSScriptRoot+'/stats-console.txt')
    $code=$LASTEXITCODE;Write-Output ('Flame armor stats audit exit='+$code)
    if(Test-Path -LiteralPath ($PSScriptRoot+'/stats.json')) {
        $report=Get-Content -LiteralPath ($PSScriptRoot+'/stats.json') -Raw | ConvertFrom-Json
        Write-Output ('Checks='+$report.checks+' Failures='+$report.failures)
        $report.results | Where-Object {-not $_.passed} | ConvertTo-Json -Depth 3
    }
    if($code -ne 0){Get-Content -LiteralPath ($PSScriptRoot+'/stats.log') -Tail 12}
    exit $code
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
