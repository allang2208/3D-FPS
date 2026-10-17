$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/M870CompletionAudit20261017'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try{$held=$gate.WaitOne(1200000)}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){exit 75}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=ShotgunAttachmentAudit -M870 -nullrhi -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/authority_engine.log"
    $result=$LASTEXITCODE
    @{exitCode=$result;mode='isolated authority and assets';realSocketTest=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/authority_process.json" -Encoding utf8
    exit $result
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
