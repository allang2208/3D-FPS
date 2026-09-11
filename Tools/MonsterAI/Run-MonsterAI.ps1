param([switch]$Audit)
$taskRoot='D:/FPS3D/FPSGAME'
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),'/Game/Tests/MonsterAI/L_MonsterAI','-game','-windowed','-ResX=1280','-ResY=720','-nosplash',('-abslog="'+$taskRoot+'/Saved/MonsterAI/play.log"'),('-ColdSteelProfile=MonsterAI_'+(Get-Date -Format yyyyMMddHHmmss)))
if($Audit){$taskArgs+=@('-MonsterAIAudit','-RenderOffscreen','-unattended')}
Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru | Select-Object Id
