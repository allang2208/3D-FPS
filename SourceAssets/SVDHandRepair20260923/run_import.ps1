param([ValidateSet('base','vertical','canted','prism','angled')][string]$Family='base')
$ErrorActionPreference='Stop'
$repairDir='D:/FPS3D/FPSGAME/SourceAssets/SVDHandRepair20260923'
$scriptPath="$repairDir/import_$Family.py"
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false;$useBridge=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(55))} catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch ended unexpectedly; preserve state.'}
 if(-not $held){throw 'UE batch is occupied; no import started.'}
 $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'})
 if($running | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}){throw 'A project commandlet is active; preserve that process.'}
 if($running.Count){$useBridge=$true}
 else {
  & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -nullrhi "-abslog=$repairDir/import_$Family.log" *> "$repairDir/import_$Family.stdout.log"
  $result=$LASTEXITCODE
  Select-String -LiteralPath "$repairDir/import_$Family.log" -Pattern 'LogPython:.*(SVD_HAND|Error|Traceback)' | Select-Object -Last 7 | ForEach-Object {$_.Line}
  if($result -ne 0){throw "UE animation import failed with exit code $result"}
 }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
if($useBridge){
 & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $scriptPath -QueueWaitSeconds 60 -OutputFile "$repairDir/import_$Family.bridge.json" -MaxOutputChars 1800
 if($LASTEXITCODE -ne 0){throw "Existing UE bridge import did not complete: $LASTEXITCODE"}
}
