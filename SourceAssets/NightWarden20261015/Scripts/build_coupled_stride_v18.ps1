param([int]$QueueWaitSeconds=1800)
$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$records=Join-Path $project 'SourceAssets\NightWarden20261015\V18CoupledLocomotion\Records'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))} catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch abandoned; preserve state'}
 if(-not $held){throw 'UE batch busy; V18 source preserved'}
 $deadline=(Get-Date).AddSeconds($QueueWaitSeconds)
 while($true){
  $processes=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe'")
  if(@($processes | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -like '*FPSGAME.uproject*'}).Count){throw 'FPSGAME editor is open; preserve it and build after user closes it'}
  $busy=@($processes | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*FPSGAME.uproject*') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')})
  if(-not $busy.Count){break}
  if((Get-Date) -gt $deadline){throw 'Engine operation still busy; source preserved'}
  Start-Sleep -Seconds 15
 }
 $stamp=Get-Date -Format 'yyyyMMdd-HHmmss';$log=Join-Path $records ('Editor-build-'+$stamp+'.log')
 & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development "-Project=$project\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$log" *> (Join-Path $records ('Editor-build-'+$stamp+'-stdout.log'))
 $code=$LASTEXITCODE
 @{exit_code=$code;log=$log;finished=(Get-Date -Format o);editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $records 'build_receipt.json') -Encoding UTF8
 Get-Content -LiteralPath $log -Tail 16
 exit $code
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
