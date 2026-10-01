param()
$ErrorActionPreference='Stop'
$fixture=Get-Content (Join-Path $PSScriptRoot 'probe.json') -Raw | ConvertFrom-Json
if ($fixture.profile -notmatch '^AKMMaterialRoute_\d{8}_\d{6}$') { throw 'Invalid isolated profile' }
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$log=Join-Path $PSScriptRoot "runtime-$stamp.log"
$commands=@(
 '50:getall FPSCastingMeshComponent SkinnedAsset',
 '51:getall FPSCastingMeshComponent OverrideMaterials',
 '52:getall WeatherViewEffectsComponent Bindings',
 '53:getall MaterialInstanceDynamic Parent',
 '54:getall MaterialInstanceDynamic ScalarParameterValues',
 '55:getall FPSWeatherManager PresentationLibrary',
 '90:quit'
) -join ','
$args=@('"D:/FPS3D/FPSGAME/FPSGAME.uproject"','/Game/GameMaps/DayNight_Lighting','-game',
 '-RenderOffscreen','-UserDir=D:/FPS3D/FPSGAME','-windowed','-ResX=640','-ResY=360','-ForceRes','-unattended','-nosound','-nosplash','-SkipStartupMenu',
 "-ColdSteelProfile=$($fixture.profile)",'-ExecCmds="t.MaxFPS 30"','-csvCaptureFrames=600',
 "-csvExecCmds=`"$commands`"","-abslog=`"$log`"")
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
 $held=$gate.WaitOne([TimeSpan]::FromSeconds(60))
 if(-not $held){throw 'UE batch gate occupied'}
 $process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args -WindowStyle Hidden -PassThru
 [pscustomobject]@{pid=$process.Id;profile=$fixture.profile;log=$log} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot "runtime-$stamp.json")
 $start=[DateTime]::UtcNow
 while(-not $process.WaitForExit(1000)) {
  if(([DateTime]::UtcNow-$start).TotalSeconds -gt 180){
   Stop-Process -Id $process.Id
   throw "Own diagnostic process exceeded 180 seconds. Log: $log"
  }
 }
 Write-Output "AKM_ROUTE_RUNTIME_EXIT $($process.ExitCode) log=$log"
 if($process.ExitCode -ne 0){throw 'Background route diagnostic failed'}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
