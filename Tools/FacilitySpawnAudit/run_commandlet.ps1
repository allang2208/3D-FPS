param([string]$TaskScript='read_saved_inputs.py',[string]$TaskStage='saved-inputs')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME';$taskOut="$taskRoot/SourceAssets/FacilitySpawnAudit20261017"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try{
 try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException]{$taskHeld=$true}
 if(-not $taskHeld){throw 'UE batch busy; nothing started.'}
 $taskDeadline=[DateTime]::UtcNow.AddMinutes(15)
 while(@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor'}).Count){
  if([DateTime]::UtcNow -gt $taskDeadline){throw 'Editor build still active; nothing started.'}
  Start-Sleep -Seconds 5
 }
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/Tools/FacilitySpawnAudit/$TaskScript" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$taskOut/CommandletUser/" "-abslog=$taskOut/Logs/$TaskStage.log" *> "$taskOut/Logs/$TaskStage-stdout.log"
 if($LASTEXITCODE -ne 0){throw "Commandlet exit $LASTEXITCODE; see $TaskStage.log"}
 Write-Output "Completed $TaskStage"
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
