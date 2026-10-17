$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    while(-not $held) {
        try{$held=$gate.WaitOne(60000)}catch [Threading.AbandonedMutexException]{$held=$true}
        if(-not $held){Write-Output 'Waiting for existing MCP batch'}
    }
    $exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $project='D:/FPS3D/FPSGAME/FPSGAME.uproject'
    & $exe $project -run=SkillNetworkAudit -FlameArmorOnly ('-Output='+$PSScriptRoot+'/authority.json') -unattended -nullrhi -Multiprocess -NoAutoSDK -nosound -NoLiveCoding ('-abslog='+$PSScriptRoot+'/authority.log') *> ($PSScriptRoot+'/authority-console.txt')
    $code=$LASTEXITCODE;Write-Output ('Armor authority audit exit='+$code)
    if($code -ne 0){Get-Content -LiteralPath ($PSScriptRoot+'/authority.log') -Tail 12;exit $code}
    Get-Content -LiteralPath ($PSScriptRoot+'/authority.json') -TotalCount 4
    & $exe $project -run=pythonscript ('-script='+$PSScriptRoot+'/check_assets.py') -unattended -nullrhi -Multiprocess -NoAutoSDK -nosound -NoLiveCoding ('-abslog='+$PSScriptRoot+'/assets.log') *> ($PSScriptRoot+'/assets-console.txt')
    $code=$LASTEXITCODE;Write-Output ('Armor asset audit exit='+$code)
    if($code -ne 0){Get-Content -LiteralPath ($PSScriptRoot+'/assets.log') -Tail 12;exit $code}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
