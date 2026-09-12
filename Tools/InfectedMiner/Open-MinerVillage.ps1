param([switch]$Audit,[switch]$Isolated)
$ErrorActionPreference='Stop'
$minerRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$minerMap=if($Isolated){'/Game/Tests/InfectedMiner/L_InfectedMiner'}else{'/Game/GameMaps/L_Normandy_FPS_Test'}
$minerArgs=@(('"'+(Join-Path $minerRoot 'FPSGAME.uproject')+'"'),$minerMap,'-game','-windowed','-ResX=1280','-ResY=720','-nosplash',('-abslog="'+(Join-Path $minerRoot 'Saved/InfectedMiner/play.log')+'"'))
if($Audit){$minerArgs+=@('-MinerAudit','-RenderOffscreen','-unattended',('-ColdSteelProfile=InfectedMinerAudit_'+(Get-Date -Format yyyyMMddHHmmss)))}
$minerStyle=if($Audit){'Hidden'}else{'Normal'}
Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $minerArgs -WindowStyle $minerStyle -PassThru | Select-Object Id
