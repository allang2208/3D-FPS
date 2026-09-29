$ErrorActionPreference = 'Stop'
$log = 'D:/FPS3D/FPSGAME/Saved/ProductionTreeHealth/editor-stub-20260929.log'
if (Test-Path $log) { Remove-Item $log -Force }
$args_ = '"D:/FPS3D/FPSGAME/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -unattended -nosplash -NoSound -NoLiveCoding -abslog="' + $log + '"'
$p = Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $args_ -WindowStyle Hidden -PassThru
Write-Output ('PID=' + $p.Id)
