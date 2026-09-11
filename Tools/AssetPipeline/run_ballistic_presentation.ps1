param([switch]$CaptureFrames,[int]$Fps=60)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$run=Get-Date -Format 'yyyyMMddHHmmss'
$log=Join-Path $root "Saved/BallisticPresentationAudit-$run.log"
$arguments=@(('"'+$root+'/FPSGAME.uproject"'),'/Game/GameMaps/DayNight_Lighting','-game','-windowed',
    '-ResX=1280','-ResY=720','-ForceRes','-unattended','-nosplash','-BallisticPresentationAudit',
    ('-ColdSteelProfile=BallisticAudit_'+$run),'-FixedSeed','-UseFixedTimeStep',('-FPS='+$Fps),('-abslog="'+$log+'"'))
if($CaptureFrames){$arguments+='-BallisticCaptureFrames'}
$process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
while(!$process.WaitForExit(1000)){}
$text=[IO.File]::ReadAllText($log)
if($process.ExitCode -ne 0 -or $text -notmatch 'BALLISTIC_COMPLETE checks=\d+ failures=0'){
    throw "Ballistic audit failed: $log"
}
Write-Output "PASS: $log"
