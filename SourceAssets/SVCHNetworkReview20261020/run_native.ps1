$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(!$held){throw 'UE batch remained busy'}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserve open editor; native audit deferred'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=ShotgunAttachmentAudit -SVCHReview -SVCHExecution -nullrhi -nosound -unattended -nop4 -nosplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0,fps.body.AsyncPreload 0' "-Output=$PSScriptRoot/native-result.json" "-abslog=$PSScriptRoot/native.log" *> "$PSScriptRoot/native-console.log"
    $code=$LASTEXITCODE
    @{exit_code=$code;completed_utc=[DateTime]::UtcNow.ToString('o');dll_sha256=(Get-FileHash 'D:/FPS3D/FPSGAME/Binaries/Win64/UnrealEditor-FPSGAME.dll').Hash;socket_transport=$false;rendered=$false}|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/native-receipt.json" -Encoding utf8
    if($code -ne 0){throw "SVCH native execution review failed: $code"}
    Write-Output 'SVCH_EXECUTION_REVIEW_COMPLETE'
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
