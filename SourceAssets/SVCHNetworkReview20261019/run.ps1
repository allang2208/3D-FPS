param([switch]$SkipBuild,[switch]$SkipImport)
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$out="$root/SourceAssets/SVCHNetworkReview20261019"
if(!$SkipBuild){ & "$out/build.ps1" }
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$held=$true}
 if(!$held){throw 'UE batch remained busy'}
 if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserve open editor; import and audit deferred'}
 $ue='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
 if(!$SkipImport){
  & $ue "$root/FPSGAME.uproject" -run=pythonscript "-script=$root/SourceAssets/SVCHReplacement20261018/QuickMeleeWrist20261019/install_profiles.py" -nullrhi -nosound -unattended -nop4 -nosplash "-abslog=$out/import.log" *> "$out/import-console.log"
  if($LASTEXITCODE -ne 0){throw 'Quick-melee profile import failed'}
 }
 & $ue "$root/FPSGAME.uproject" -run=ShotgunAttachmentAudit -SVCHReview -nullrhi -nosound -unattended -nop4 -nosplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0,fps.body.AsyncPreload 0' "-Output=$out/native-result.json" "-abslog=$out/native.log" *> "$out/native-console.log"
 $exitCode=$LASTEXITCODE
 @{exit_code=$exitCode;completed_utc=[DateTime]::UtcNow.ToString('o');dll_sha256=(Get-FileHash "$root/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;socket_transport=$false;rendered=$false}|ConvertTo-Json|Set-Content -LiteralPath "$out/native-receipt.json" -Encoding utf8
 if($exitCode -ne 0){throw "Native review failed: $exitCode"}
 Write-Output 'SVCH_NATIVE_REVIEW_COMPLETE'
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
