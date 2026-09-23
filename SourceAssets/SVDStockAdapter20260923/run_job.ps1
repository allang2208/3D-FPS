param([string]$Script='import_assets.py')
$ErrorActionPreference='Stop'
$jobDir='D:/FPS3D/FPSGAME/SourceAssets/SVDStockAdapter20260923'
$scriptPath=Join-Path $jobDir $Script
$job=[IO.Path]::GetFileNameWithoutExtension($Script)
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false;$bridge=$false
try {
 try {
  $queueUntil=(Get-Date).AddMinutes(10)
  do {$held=$gate.WaitOne([TimeSpan]::FromSeconds(50))} while(-not $held -and (Get-Date) -lt $queueUntil)
 } catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch ended unexpectedly; preserve state.'}
 if(-not $held){throw 'UE batch gate occupied; nothing changed.'}
 $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'})
 if($running | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}){throw 'Project commandlet is running; preserve state.'}
 if($running.Count){$bridge=$true}
 else {
  if($Script -eq 'end_play.py'){Write-Output 'SVD_STOCK_NO_EDITOR_RUNNING';return}
  & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -nullrhi "-abslog=$jobDir/$job.log" *> "$jobDir/$job.stdout.log"
  $result=$LASTEXITCODE
  Select-String -LiteralPath "$jobDir/$job.log" -Pattern 'LogPython:.*(SVD_STOCK_|Error|Traceback)' | Select-Object -Last 8 | ForEach-Object {$_.Line}
  if($result -ne 0){throw "UE import failed: $result"}
 }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
if($bridge){
 $stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
 & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $scriptPath -QueueWaitSeconds 60 -OutputFile "$jobDir/$job.$stamp.bridge.json" -MaxOutputChars 2200
 if($LASTEXITCODE -ne 0){throw "Existing bridge import did not complete: $LASTEXITCODE"}
}
