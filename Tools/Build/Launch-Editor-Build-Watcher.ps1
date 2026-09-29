$p = Start-Process powershell -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','D:/FPS3D/FPSGAME/SourceAssets/DungeonSpawn20260925/Scripts/watcher-editorbuild-hpmult-20260928.ps1') -WindowStyle Hidden -PassThru
Start-Sleep 6
Write-Output ("PID=" + $p.Id + " Alive=" + (-not $p.HasExited))
Get-Content 'D:/FPS3D/FPSGAME/Saved/BuildEditor/watcher-editorbuild-hpmult-20260928.status' -Tail 2
