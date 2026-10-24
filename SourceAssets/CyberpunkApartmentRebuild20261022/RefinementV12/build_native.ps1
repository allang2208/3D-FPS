param([int]$MaximumWaitSeconds=7200)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskRoot 'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV12'
$taskPattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try{
 while($true){
  if([DateTime]::UtcNow -gt $taskDeadline){throw 'Existing project process retained; build pending.'}
  $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match $taskPattern) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
  if($taskOwners.Count){Start-Sleep -Seconds 8;continue}
  try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(8))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
  if(-not $taskHeld){continue}
  $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match $taskPattern) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
  if(-not $taskOwners.Count){break}
  $taskGate.ReleaseMutex();$taskHeld=$false;Start-Sleep -Seconds 8
 }
 $taskResults=@()
 foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')){
  $taskLog=Join-Path $taskOutput ('build-'+$taskTarget+'-01.log')
  & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -WaitMutex -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> (Join-Path $taskOutput ('build-'+$taskTarget+'-01-console.log'))
  $taskExit=$LASTEXITCODE;$taskResults+=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog}
  @{targets=$taskResults;game_run=$false;interactive_editor_opened=$false} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskOutput 'build-receipt.json') -Encoding utf8
  if($taskExit -ne 0){throw ('Native build failed: '+$taskTarget)}
 }
 Write-Output 'Apartment door Editor and Game binaries built.'
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
