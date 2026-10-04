param([int]$MaximumWaitSeconds=600,[string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$recordRoot=Join-Path $projectRoot 'SourceAssets/HangingBellM09Meshy20261003/LocomotionV19/Records'
$buildTool='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
foreach($targetName in $Targets) {
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
  if($activeBuilds.Count -gt 0){
   # Resume when the existing compiler exits; do not repeatedly submit UBT jobs.
   Wait-Process -Id $activeBuilds.ProcessId -Timeout 50 -ErrorAction SilentlyContinue
  }else{Start-Sleep -Seconds 10}
 }
 # Preserve the configuration already compiled in the shared checkout. Toggling
 # WITH_LIVE_CODING recompiles the entire project even for an incremental build.
 $modeArgs=@()
 $definitions=Join-Path $projectRoot ('Intermediate/Build/Win64/x64/'+$targetName+'/Development/Core/SharedDefinitions.Core.Cpp20.h')
 if((Test-Path -LiteralPath $definitions) -and [IO.File]::ReadAllText($definitions) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$modeArgs+= '-NoLiveCoding'}
 $log=Join-Path $recordRoot ('build_'+$targetName+'.log')
 & $buildTool $targetName Win64 Development ('-Project='+$projectRoot+'/FPSGAME.uproject') -NoHotReload -NoHotReloadFromIDE @modeArgs -MaxParallelActions=4 ('-Log='+$log) *> (Join-Path $recordRoot ('build_'+$targetName+'_stdout.log'))
 $result=$LASTEXITCODE
 Write-Output ('M09_BUILD_RESULT '+$targetName+' '+$result)
 if($result -ne 0){exit $result}
}
