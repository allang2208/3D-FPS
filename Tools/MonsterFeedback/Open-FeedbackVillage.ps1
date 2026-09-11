$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),'/Game/GameMaps/L_Normandy_FPS_Test','-game','-windowed','-ForceRes','-ResX=1280','-ResY=720','-NoSplash',('-abslog="'+$taskRoot+'/SourceAssets/MonsterFeedback20260911/manual-village.log"'),('-ColdSteelProfile=MonsterFeedback_Playtest_'+(Get-Date -Format yyyyMMddHHmmss)),'-ExecCmds="BugItGo -2479.354 32131.095 -11396.745 -6 150 0,r.ScreenPercentage 80,r.Streaming.PoolSize 1800,r.Shadow.Virtual.MaxPhysicalPages 1536"')
# Visible interactive village requested by the user; tests use Run-Regression instead.
Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Normal -PassThru | Select-Object Id
