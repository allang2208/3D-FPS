$ErrorActionPreference='Stop'
$reviewRoot='D:/FPS3D/FPSGAME'
$reviewOut="$reviewRoot/SourceAssets/Saiga12KThirdPerson20261018/Receipts"
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$reviewHeld=$false
try {
 try {$reviewHeld=$reviewGate.WaitOne([TimeSpan]::FromMinutes(5))}catch [Threading.AbandonedMutexException]{$reviewHeld=$true;throw 'Abandoned UE batch; preserve shared state.'}
 if(-not $reviewHeld){throw 'Shared UE batch is occupied; no third-person audit process started.'}
 if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Interactive editor reopened; preserve its state.'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$reviewRoot/FPSGAME.uproject" -run=ShotgunAttachmentAudit -Saiga12KPresentation -nullrhi -unattended -nop4 -nosound -nosplash "-abslog=$reviewOut/audit.log" *> "$reviewOut/audit-console.log"
 $reviewExit=$LASTEXITCODE
 @{exit_code=$reviewExit;completed=(Get-Date).ToString('o');mode='isolated native third-person graph and real assets';rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$reviewOut/audit-process.json" -Encoding utf8
 exit $reviewExit
} finally {if($reviewHeld){$reviewGate.ReleaseMutex()};$reviewGate.Dispose()}
