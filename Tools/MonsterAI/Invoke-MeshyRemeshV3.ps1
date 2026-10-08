param(
 [ValidateSet('SpiralPillarM14','HangingBellM09','M10Mawcrawler','LurkerM08')][string]$Species,
 [ValidateSet('import','corpse')][string]$Stage,
 [ValidateSet('MeshyRemeshV3','M14TeethV4','AnatomyRepairV5')][string]$Revision='MeshyRemeshV3'
)
$ErrorActionPreference='Stop'
if(-not $Species -or -not $Stage){throw 'Species and Stage are required.'}
$taskProject='D:/FPS3D/FPSGAME'
$taskRevisionFolder='RemeshV3'
$taskModuleFolder='MonsterAI'
$taskModule='install_meshy_remesh_v3'
if($Revision -eq 'M14TeethV4'){
 if($Species -ne 'SpiralPillarM14'){throw 'M14TeethV4 is only for SpiralPillarM14.'}
 $taskRevisionFolder='RemeshV4Teeth'
 $taskModuleFolder='SpiralPillarM14'
 $taskModule='install_teeth_remesh_v4'
}
if($Revision -eq 'AnatomyRepairV5'){
 if($Species -eq 'SpiralPillarM14'){throw 'AnatomyRepairV5 only applies to M08, M09 and M10.'}
 $taskRevisionFolder='AnatomyRepairV5'
 $taskModule='install_anatomy_repair_v5'
}
$taskOutput=Join-Path $taskProject "SourceAssets/AlienGeometry20261006/$taskRevisionFolder/$Species"
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskDeadline=[DateTime]::UtcNow.AddMinutes(30)
try {
 while(-not $taskHeld){
  if([DateTime]::UtcNow -gt $taskDeadline){throw 'Asset batch stayed occupied; no other process was stopped.'}
  $taskProcesses=@(Get-CimInstance Win32_Process)
  if(@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){
   $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
   $taskEntry=Join-Path $taskOutput "entry-$Stage-$taskStamp.py"
   $taskCode="import sys,importlib`nsys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/$taskModuleFolder')`nimport $taskModule as p`nimportlib.reload(p)`np.run('$Species','$Stage')`n"
   [IO.File]::WriteAllText($taskEntry,$taskCode,[Text.UTF8Encoding]::new($false))
   & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskEntry -OutputFile (Join-Path $taskOutput "bridge-$Stage-$taskStamp.txt") -MaxOutputChars 1800 -QueueWaitSeconds 1800 -RequestTimeoutSeconds 600
   if($LASTEXITCODE -ne 0){throw 'Asset batch did not complete. See the saved receipt.'}
   $taskState=Get-Content (Join-Path $taskOutput 'installation.json') -Raw|ConvertFrom-Json
   if($taskState.stage -eq 'waiting_for_pie'){Start-Sleep -Seconds 30;continue}
   break
  }
  try{$taskHeld=$taskGate.WaitOne(1000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
  while($taskHeld){
   $taskProcesses=@(Get-CimInstance Win32_Process)
   if(@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count){$taskGate.ReleaseMutex();$taskHeld=$false;break}
   $taskBusy=@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe' -or ($_.Name -in @('UnrealBuildTool.exe','dotnet.exe') -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor')})
   if(-not $taskBusy.Count){break}
   if([DateTime]::UtcNow -gt $taskDeadline){throw 'Background asset/build window stayed occupied.'}
   Start-Sleep -Seconds 5
  }
 }
 if($taskHeld){
  if(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')}).Count){throw 'Editor appeared before import; no asset changed.'}
  $taskScript=Join-Path $taskProject "Tools/$taskModuleFolder/$taskModule.py"
  & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" "-RemeshSpecies=$Species" "-RemeshStage=$Stage" -unattended -nop4 -nosound -NullRHI -NoSplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$taskOutput/$Stage-$taskStamp.log" *> (Join-Path $taskOutput "console-$Stage-$taskStamp.log")
  if($LASTEXITCODE -ne 0){throw "Asset batch failed: $Species $Stage"}
 }
 $taskReceipt=Get-Content (Join-Path $taskOutput 'installation.json') -Raw|ConvertFrom-Json
 if($taskReceipt.error){throw $taskReceipt.error}
 if($Stage -eq 'import' -and -not $taskReceipt.live_imported){throw 'Live asset has not saved.'}
 if($Stage -eq 'corpse' -and -not $taskReceipt.complete){throw 'Corpse asset has not saved and bound.'}
 Write-Output "$Species $Stage saved."
} finally {
 if($taskHeld){$taskGate.ReleaseMutex()}
 $taskGate.Dispose()
}
