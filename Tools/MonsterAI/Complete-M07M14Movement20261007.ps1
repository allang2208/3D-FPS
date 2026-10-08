param([int]$MaximumWaitSeconds=600,[string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskRecords=Join-Path $taskProject 'SourceAssets/M07M14Movement20261007/Records'
$taskBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
New-Item -ItemType Directory -Path $taskRecords -Force | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try{
 try{$taskHeld=$taskGate.WaitOne($MaximumWaitSeconds*1000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
 if(-not $taskHeld){throw 'Existing UE batch is still occupied; no build submitted.'}
foreach($taskTarget in $Targets){
 $taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
 while($true){
  $taskProcesses=@(Get-CimInstance Win32_Process)
  $taskBuilds=@($taskProcesses | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
  $taskOwners=@($taskProcesses | Where-Object {
   if($taskTarget -eq 'FPSGAMEEditor'){
    $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME')
   }else{$_.Name -match '^FPSGAME(-Win64-.+)?\.exe$'}
  })
  if($taskOwners.Count){
   if(@($taskOwners | Where-Object {$_.Name -ne 'UnrealEditor-Cmd.exe'}).Count){throw ('Preserving the running binary owner; close it before building '+$taskTarget)}
   if([DateTime]::UtcNow -ge $taskDeadline){throw 'Existing commandlet is still running; no build submitted.'}
   Wait-Process -Id $taskOwners.ProcessId -Timeout 45 -ErrorAction SilentlyContinue
   continue
  }
  if(-not $taskBuilds.Count){break}
  if([DateTime]::UtcNow -ge $taskDeadline){throw 'Existing build is still running; no competing build submitted.'}
  Wait-Process -Id $taskBuilds.ProcessId -Timeout 45 -ErrorAction SilentlyContinue
 }
 $taskMode=@()
 $taskDefinitions=Join-Path $taskProject ('Intermediate/Build/Win64/x64/'+$taskTarget+'/Development/Core/SharedDefinitions.Core.Cpp20.h')
 if((Test-Path -LiteralPath $taskDefinitions) -and [IO.File]::ReadAllText($taskDefinitions) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$taskMode+='-NoLiveCoding'}
 $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
 $taskLog=Join-Path $taskRecords ('build-'+$taskTarget+'-'+$taskStamp+'.log')
 & $taskBuild $taskTarget Win64 Development ('-Project='+$taskProject+'/FPSGAME.uproject') -NoHotReload -NoHotReloadFromIDE @taskMode -MaxParallelActions=4 ('-Log='+$taskLog) *> (Join-Path $taskRecords ('stdout-'+$taskTarget+'-'+$taskStamp+'.log'))
 $taskExit=$LASTEXITCODE
 $taskReceipt=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog;finished_at=[DateTime]::Now.ToString('o');tests_run=$false;editor_started=$false}
 $taskReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRecords ('build-'+$taskTarget+'.json')) -Encoding utf8
 Write-Output ($taskTarget+' build exit '+$taskExit)
 if($taskExit -ne 0){throw ('Build failed; see '+$taskLog)}
}
$taskAssetOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')})
if($taskAssetOwners.Count){throw 'An editor owns assets; preserving it without starting another process.'}
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskAssetScript=Join-Path $taskProject 'Tools/MonsterAI/save_m07_m14_movement_20261007.py'
$taskAssetLog=Join-Path $taskRecords ('asset-save-'+$taskStamp+'.log')
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskAssetScript" -unattended -nop4 -nosound -NullRHI -NoSplash "-abslog=$taskAssetLog" *> (Join-Path $taskRecords ('asset-console-'+$taskStamp+'.log'))
if($LASTEXITCODE -ne 0){throw ('Asset save failed; see '+$taskAssetLog)}
$taskAssetReceipt=Get-Content -LiteralPath (Join-Path $taskRecords 'ue_revision.json') -Raw | ConvertFrom-Json
if(-not $taskAssetReceipt.complete){throw 'M07/M14 movement Blueprints were not saved.'}
Write-Output 'M07 and M14 movement Blueprints saved.'
}finally{
 if($taskHeld){$taskGate.ReleaseMutex()}
 $taskGate.Dispose()
}
