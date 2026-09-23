param([string]$Script='read_ue.py')
$ErrorActionPreference='Stop'
$auditDir='D:/FPS3D/FPSGAME/SourceAssets/SVDContactAudit20260923'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(55))} catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch ended unexpectedly; preserve state.'}
 if(-not $held){throw 'UE batch is occupied; no operation started.'}
 $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'})
 if($editors.Count){throw 'FPSGAME process present; preserve existing process.'}
 $job=[IO.Path]::GetFileNameWithoutExtension($Script)
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$auditDir/$Script" -unattended -nop4 -nosplash -nullrhi "-abslog=$auditDir/$job.log" *> "$auditDir/$job.stdout.log"
 exit $LASTEXITCODE
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
