param([int]$MaximumWaitSeconds=600)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject 'Saved/MSeriesMovementAudit20261007'
New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try{
 try{$taskHeld=$taskGate.WaitOne($MaximumWaitSeconds*1000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
 if(-not $taskHeld){throw 'Existing UE batch is still occupied; read-only commandlet not submitted.'}
 $taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
 while($true){
  $taskProcesses=@(Get-CimInstance Win32_Process)
  if(@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){throw 'Preserving running editor; use the existing bridge for the read-only batch.'}
  $taskBusy=@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
  if(-not $taskBusy.Count){break}
  if([DateTime]::UtcNow -ge $taskDeadline){throw 'Background window stayed occupied; no other process was stopped.'}
  Wait-Process -Id $taskBusy.ProcessId -Timeout 30 -ErrorAction SilentlyContinue
 }
 $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
 $taskScript=Join-Path $taskProject 'Tools/MonsterAI/read_m_series_movement_20261007.py'
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosound -NullRHI -NoSplash "-abslog=$taskOutput/read-$taskStamp.log" *> (Join-Path $taskOutput "console-$taskStamp.log")
 if($LASTEXITCODE -ne 0){throw 'Read-only snapshot failed; see audit logs.'}
 Write-Output 'M-series saved defaults read without saving assets.'
}finally{
 if($taskHeld){$taskGate.ReleaseMutex()}
 $taskGate.Dispose()
}
