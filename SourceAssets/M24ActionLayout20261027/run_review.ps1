param([Parameter(Mandatory=$true)][string]$Label,[switch]$Baseline)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot="$projectRoot/SourceAssets/M24ActionLayout20261027"
if($Label -notmatch '^[a-zA-Z0-9_-]+$'){throw 'Invalid review label'}
$output="$taskRoot/$Label"
if(Test-Path -LiteralPath $output){throw 'Use a fresh review label'}
New-Item -ItemType Directory -Path $output | Out-Null
$argsList=@(('"'+$projectRoot+'/FPSGAME.uproject"'),'/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
 '-game','-RenderOffscreen','-windowed','-ResX=1920','-ResY=1080','-ForceRes','-unattended','-nosplash','-nosound','-NoSteam','-SkipStartupMenu','-UseFixedTimeStep','-FPS=60','-M24ActionAudit',
 ('-ColdSteelProfile=M24ActionAudit_'+$Label),('-M24ReviewOutput="'+$output+'"'),('-UserDir="'+$output+'/User/"'),('-abslog="'+$output+'/runtime.log"'))
if($Baseline){$argsList+='-M24Baseline'}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
 try{$held=$gate.WaitOne(600000)}catch [Threading.AbandonedMutexException]{$held=$true}
 if(-not $held){throw 'UE batch is occupied'}
 $active=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
 if($active.Count){throw 'Existing project process retained; do not overlap the review'}
 $reviewProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
 Write-Output "M24 isolated game review PID $($reviewProcess.Id); output $output"
 $reviewProcess.WaitForExit()
 if($reviewProcess.ExitCode -ne 0 -or -not(Test-Path "$output/runtime.json")){throw 'M24 review incomplete; inspect runtime.log'}
 Write-Output 'M24 full animation review saved.'
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
