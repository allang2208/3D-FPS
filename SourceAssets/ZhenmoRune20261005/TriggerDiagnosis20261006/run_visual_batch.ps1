param([string]$Label='exposure',[switch]$SkipBuild,[switch]$SkipAssets)
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$root='D:/FPS3D/FPSGAME';$out=Join-Path $root 'SourceAssets/ZhenmoRune20261005/TriggerDiagnosis20261006'
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(15))} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'UE batch queue timeout'}
 $deadline=[DateTime]::UtcNow.AddMinutes(15)
 do {
  if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Existing editor preserved; test batch not started'}
  $busy=Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}
  if(-not $busy){break}
  if([DateTime]::UtcNow -gt $deadline){throw 'Other build/import still active; preserved'}
  Start-Sleep -Seconds 5
 } while($true)
 if(-not $SkipBuild){
  & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex *> (Join-Path $out 'test-build.log')
  if($LASTEXITCODE -ne 0){throw 'Test build failed'}
  Write-Output 'ZHENMO_TEST_BUILD_COMPLETE'
 }
 if(-not $SkipAssets){
  $assetArgs=@("$root/FPSGAME.uproject",'-run=pythonscript',"-script=$out/install_exposure.py",'-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$out/exposure-import.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
  & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @assetArgs *> (Join-Path $out 'exposure-console.log')
  if($LASTEXITCODE -ne 0){throw 'Exposure authoring failed'}
  Write-Output 'ZHENMO_EXPOSURE_ASSETS_SAVED'
 }
 $testArgs=@("$root/FPSGAME.uproject",'/Game/GameMaps/DayNight_Lighting','-game','-multiprocess','-RenderOffscreen','-windowed','-ResX=1280','-ResY=900','-ForceRes','-unattended','-nosplash','-nop4','-nosound','-ColdSteelProfile=ZhenmoVisualAudit20261006','-ZhenmoVisualAudit','-ZhenmoAuditExit',"-ZhenmoAuditLabel=$Label",'-ClearwaterNoMenu','-SkipStartupMenu','-ExecCmds="fps.Zhenmo.VisualAudit,t.MaxFPS 45,DisableAllScreenMessages"',"-abslog=$out/standalone-$Label.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
 $p=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $testArgs -WindowStyle Hidden -PassThru
 Write-Output ('ZHENMO_TEST_RUNNING_PID '+$p.Id)
 $p.WaitForExit()
 Write-Output ('ZHENMO_TEST_EXIT '+$p.ExitCode)
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}