param([switch]$Audit)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),'/Game/GameMaps/L_Normandy_FPS_Test','-game','-windowed','-ResX=1280','-ResY=720','-NoSplash',('-abslog="'+$taskRoot+'/Saved/HandBrain/play.log"'))
if($Audit){$taskArgs+=@('-HandBrainAudit','-RenderOffscreen','-unattended',('-ColdSteelProfile=HandBrainAudit_'+(Get-Date -Format 'yyyyMMddHHmmss')))}
$taskWindow=if($Audit){'Hidden'}else{'Normal'}
Start-Process -FilePath $taskEngine -ArgumentList $taskArgs -WindowStyle $taskWindow -PassThru | Select-Object Id
