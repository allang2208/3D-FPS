param([int]$MaximumWaitSeconds=600)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$recordRoot=Join-Path $projectRoot 'SourceAssets/HangingBellM09Meshy20261003/ResonanceV06/Records'
$buildTool='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
foreach($targetName in @('FPSGAMEEditor','FPSGAME')) {
 $deadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
 $announced=$false
 while($true) {
  $activeBuilds=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe' })
  $dllOwners=@()
  if($targetName -eq 'FPSGAMEEditor') {
   $dllOwners=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME' })
  }
  if($activeBuilds.Count -eq 0 -and $dllOwners.Count -eq 0){break}
  if(-not $announced){Write-Output ('M09 waiting for existing build / DLL owner before '+$targetName);$announced=$true}
  if([DateTime]::UtcNow -ge $deadline){Write-Output ('M09_BUILD_DEFERRED '+$targetName);exit 75}
  Start-Sleep -Seconds 10
 }
 $log=Join-Path $recordRoot ('build_'+$targetName+'.log')
 & $buildTool $targetName Win64 Development ('-Project='+$projectRoot+'/FPSGAME.uproject') -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 ('-Log='+$log) *> (Join-Path $recordRoot ('build_'+$targetName+'_stdout.log'))
 $result=$LASTEXITCODE
 Write-Output ('M09_BUILD_RESULT '+$targetName+' '+$result)
 if($result -ne 0){exit $result}
}
