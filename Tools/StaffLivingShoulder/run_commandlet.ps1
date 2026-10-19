param([string]$TaskScript='read_current_assets.py',[string]$TaskStage='read-current',[switch]$WritesAssets)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOutput="$taskRoot/SourceAssets/StaffLivingShoulder20261017"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
 try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
 if (-not $taskHeld) {throw 'UE asset batch is busy; no process started.'}
 $taskDeadline=[DateTime]::UtcNow.AddMinutes(10)
 do {
  $taskProcesses=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor|^dotnet.exe$'})
  if ($WritesAssets -and @($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count -gt 0) {throw 'An editor is active. Preserve loaded assets; use the existing editor bridge instead.'}
  # Inspected independent commandlets write only weather probe JSON, Voxel20 savegames and
  # /Game/Items/ProductionTools/ShovelGrip20261017, respectively. A Game-target
  # build does not replace the Editor module loaded by this asset commandlet.
  $taskBusy=@($taskProcesses | Where-Object {
   ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject' -and $_.CommandLine -notmatch 'Saved[\\/]probe_iso2\.py|SourceAssets[\\/]ShovelGrip20261017[\\/]import_shovel\.py|SourceAssets[\\/]UDSBridge20261017[\\/]probe10\.py') -or
   ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor')
  }).Count -gt 0
  if ($taskBusy) {
   if ([DateTime]::UtcNow -ge $taskDeadline) {throw 'Project is still occupied after ten minutes; no new commandlet started.'}
   Start-Sleep -Seconds 5
  }
 } while ($taskBusy)
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/Tools/StaffLivingShoulder/$TaskScript" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$taskOutput/CommandletUser/" "-abslog=$taskOutput/Logs/$TaskStage.log" *> "$taskOutput/Logs/$TaskStage-stdout.log"
 $taskExit=$LASTEXITCODE
 if ($taskExit -ne 0) {throw "Commandlet exit $taskExit. See $taskOutput/Logs/$TaskStage.log"}
 Write-Output "Background asset step completed: $TaskStage"
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
