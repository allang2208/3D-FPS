param([switch]$Audit,[switch]$Village)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskMap=if($Village){'/Game/GameMaps/L_Normandy_FPS_Test'}else{'/Game/Tests/PoisonMaggot/L_PoisonMaggot'}
$taskLog=if($Village){'village-play.log'}else{'play.log'}
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),$taskMap,'-game','-windowed','-ResX=1280','-ResY=720','-NoSplash',('-abslog="'+$taskRoot+'/Saved/PoisonMaggot/'+$taskLog+'"'),('-ColdSteelProfile=PoisonMaggot_'+(Get-Date -Format yyyyMMddHHmmss)))
if($Audit){$taskAudit=if($Village){'-PoisonMaggotVillageAudit'}else{'-PoisonMaggotAudit'};$taskArgs+=@($taskAudit,'-RenderOffscreen','-unattended')}
if($Audit -and $Village){$taskArgs+='-ExecCmds="r.ScreenPercentage 60,r.Streaming.PoolSize 1500,r.Shadow.Virtual.MaxPhysicalPages 1024"'}
Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru | Select-Object Id
