param([int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$records=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\V14BareBodyHand\Records'))
$scriptFile=Join-Path $PSScriptRoot 'install_bare_body_hand_v14.py'
New-Item -ItemType Directory -Force -Path $records | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))}
 catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch abandoned; preserve state'}
 if(-not $held){throw 'UE batch occupied; V14 complete body source and exports preserved'}
 $live=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains('d:/fps3d/fpsgame/fpsgame.uproject')})
 if($live.Count){
  if(@($live | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}).Count){throw 'A project commandlet owns the assets; preserve its work'}
  & "$projectRoot\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript $scriptFile -QueueWaitSeconds 0 -MaxOutputChars 3000 -OutputFile (Join-Path $records ('Install-live-'+$stamp+'.txt'))
 } else {
  $activeBuild=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -like '*UnrealBuildTool*'})
  if($activeBuild.Count){throw 'Engine build is using the binaries; preserve its work'}
  $log=Join-Path $records ('Install-commandlet-'+$stamp+'.log')
  $stdout=Join-Path $records ('Install-stdout-'+$stamp+'.log')
  & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$projectRoot\FPSGAME.uproject" '-run=pythonscript' "-script=$scriptFile" '-Multiprocess' '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' "-abslog=$log" *> $stdout
  $code=$LASTEXITCODE
  Get-Content -LiteralPath $stdout -Tail 16
  Write-Output "NIGHT_WARDEN_V14_INSTALL_EXIT=$code"
  exit $code
 }
 exit $LASTEXITCODE
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
