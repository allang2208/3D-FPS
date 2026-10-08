$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskScript=Join-Path $taskProject 'Tools/MonsterAI/read_three_remesh_assets.py'
$taskOutput=Join-Path $taskProject 'SourceAssets/AlienGeometry20261006/AnatomyInspection20261007'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskDeadline=[DateTime]::UtcNow.AddMinutes(20)
try {
 while(-not $taskHeld){
  if([DateTime]::UtcNow -gt $taskDeadline){throw 'Read window stayed occupied; no other process was stopped.'}
  $taskProcesses=@(Get-CimInstance Win32_Process)
  if(@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){
   & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript -OutputFile (Join-Path $taskOutput "read-bridge-$taskStamp.txt") -MaxOutputChars 1800 -QueueWaitSeconds 1200 -RequestTimeoutSeconds 300
   if($LASTEXITCODE -ne 0){throw 'Read-only bridge batch did not complete.'}
   break
  }
  if(@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -or ($_.Name -in @('UnrealBuildTool.exe','dotnet.exe') -and $_.CommandLine -match 'UnrealBuildTool')}).Count){Start-Sleep -Seconds 5;continue}
  try{$taskHeld=$taskGate.WaitOne(1000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
 }
 if($taskHeld){
  if(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')}).Count){throw 'An editor appeared before the read batch; no asset changed.'}
  & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosound -NullRHI -NoSplash "-abslog=$taskOutput/read-$taskStamp.log" *> (Join-Path $taskOutput "console-$taskStamp.log")
  if($LASTEXITCODE -ne 0){throw 'Read-only asset inspection failed; see saved log.'}
 }
 $taskReport=Get-Content (Join-Path $taskOutput 'runtime.json') -Raw|ConvertFrom-Json
 if(-not $taskReport.complete){throw 'Read-only inspection did not finish.'}
 Write-Output 'Three live meshes and corpse bindings read; no production assets saved.'
}finally{
 if($taskHeld){$taskGate.ReleaseMutex()}
 $taskGate.Dispose()
}
