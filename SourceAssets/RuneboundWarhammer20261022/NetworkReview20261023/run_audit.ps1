$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    while(-not $held){try{$held=$gate.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$held=$true}}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=RuneboundReviewAudit' "-Report=$PSScriptRoot/authority.json" '-nullrhi' '-nosound' '-unattended' '-nop4' '-NoLiveCoding' "-abslog=$PSScriptRoot/authority.log"
    exit $LASTEXITCODE
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
