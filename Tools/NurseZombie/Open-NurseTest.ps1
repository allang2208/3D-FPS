param([switch]$Audit)
$ErrorActionPreference='Stop'
$nurseRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$nurseEngine='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$nurseArgs=@(('"'+(Join-Path $nurseRoot 'FPSGAME.uproject')+'"'),'/Game/GameMaps/L_Normandy_FPS_Test','-game','-windowed','-ResX=1280','-ResY=720','-nosplash',('-abslog="'+(Join-Path $nurseRoot 'Saved/NurseZombie/play.log')+'"'))
if ($Audit) { $nurseArgs+=@('-NurseAudit','-NurseCapture','-unattended') }
$nurseWindowStyle=if ($Audit) {'Hidden'} else {'Normal'}
Start-Process -FilePath $nurseEngine -ArgumentList $nurseArgs -WindowStyle $nurseWindowStyle
