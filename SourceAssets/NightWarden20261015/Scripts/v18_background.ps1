param([ValidateSet('Inspect','Install','Verify')][string]$Stage='Inspect',[int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$records=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\V18CoupledLocomotion\Records'))
$scripts=@{Inspect='read_retarget_state_v18.py';Install='install_coupled_stride_v18.py';Verify='read_installed_stride_v18.py'}
$scriptFile=Join-Path $PSScriptRoot $scripts[$Stage]
New-Item -ItemType Directory -Force -Path $records | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))}
 catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch abandoned; preserve state'}
 if(-not $held){throw 'UE batch occupied; V18 source is preserved'}
 $ownerDeadline=(Get-Date).AddSeconds($QueueWaitSeconds)
 while($true){
  $live=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains('d:/fps3d/fpsgame/fpsgame.uproject')})
  $commandletBusy=@($live | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}).Count -gt 0
  $buildBusy=($live.Count -eq 0) -and (@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -like '*UnrealBuildTool*'}).Count -gt 0)
  if(-not ($commandletBusy -or $buildBusy)){break}
  if((Get-Date) -gt $ownerDeadline){throw 'Existing engine operation has not released the project; V18 source is preserved'}
  Start-Sleep -Seconds 15
 }
 if($live.Count){
  & "$projectRoot\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript $scriptFile -QueueWaitSeconds 0 -MaxOutputChars 3000 -OutputFile (Join-Path $records ($Stage+'-live-'+$stamp+'.txt'))
 } else {
  $log=Join-Path $records ($Stage+'-commandlet-'+$stamp+'.log')
  $stdout=Join-Path $records ($Stage+'-stdout-'+$stamp+'.log')
  & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$projectRoot\FPSGAME.uproject" '-run=pythonscript' "-script=$scriptFile" '-Multiprocess' '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' "-abslog=$log" *> $stdout
  $code=$LASTEXITCODE
  Get-Content -LiteralPath $stdout -Tail 16
  Write-Output "NIGHT_WARDEN_V18_${Stage}_EXIT=$code"
  exit $code
 }
 exit $LASTEXITCODE
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
