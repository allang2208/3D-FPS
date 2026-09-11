param([ValidateSet('Maggot','Arena','HandBrain','Status','AI','Nurse')][string]$Mode='Maggot',[string]$Label='current',[int]$Width=1280,[int]$Height=720,[float]$CorpseYaw=0)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskFlag=switch($Mode){'Maggot'{'-PoisonMaggotVillageAudit'} 'HandBrain'{'-HandBrainAudit'} 'Status'{'-StatusEffectsAudit'} 'Arena'{'-PoisonMaggotAudit'} 'AI'{'-MonsterAIAudit'} 'Nurse'{'-NurseAudit'}}
$taskMap=if($Mode -in @('Status','Arena')){'/Game/Tests/PoisonMaggot/L_PoisonMaggot'}elseif($Mode -eq 'AI'){'/Game/Tests/MonsterAI/L_MonsterAI'}else{'/Game/GameMaps/L_Normandy_FPS_Test'}
$taskLog=$taskRoot+'/SourceAssets/MonsterFeedback20260911/'+$Mode+'-'+$Label+'.log'
$taskArgs=@(('"'+$taskRoot+'/FPSGAME.uproject"'),$taskMap,'-game','-windowed','-ForceRes',('-ResX='+$Width),('-ResY='+$Height),('-HandBrainCorpseYaw='+$CorpseYaw),'-NoSplash','-RenderOffscreen','-unattended',$taskFlag,'-MonsterFeedbackProbe',('-abslog="'+$taskLog+'"'),('-ColdSteelProfile=MonsterFeedback_'+$Mode+'_'+(Get-Date -Format yyyyMMddHHmmss)),'-ExecCmds="r.ScreenPercentage 70,r.Streaming.PoolSize 1500,r.Shadow.Virtual.MaxPhysicalPages 1024"')
Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WindowStyle Hidden -PassThru | Select-Object Id
