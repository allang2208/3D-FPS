param([int[]]$Widths=@(1280,960))
$taskEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$taskOut='D:/FPS3D/FPSGAME/Saved/AmmoReadout20260909'
New-Item -ItemType Directory -Force $taskOut | Out-Null
foreach($taskWidth in $Widths){
    if($taskWidth -notin @(960,1280,1920)){throw 'Unsupported preview width'}
    $taskHeight=[int]($taskWidth*9/16)
    $taskLog="$taskOut/$taskWidth.log"
    $taskArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','/Game/GameMaps/DayNight_Lighting','-game','-windowed',"-ResX=$taskWidth","-ResY=$taskHeight",'-ForceRes','-unattended','-nosound','-NoSplash','-AmmoReadoutAudit',"-ColdSteelProfile=AmmoReadoutAudit_${taskWidth}","-abslog=$taskLog")
    $taskProcess=Start-Process -FilePath $taskEngine -ArgumentList $taskArgs -PassThru -WindowStyle Hidden
    if(-not $taskProcess.WaitForExit(60000)){
        Write-Output "Preview running PID=$($taskProcess.Id) log=$taskLog"
        if(-not $taskProcess.WaitForExit(60000)){throw 'Preview timeout; process retained'}
    }
    $taskText=[IO.File]::ReadAllText($taskLog)
    if($taskProcess.ExitCode -ne 0 -or $taskText -notmatch 'AmmoReadoutPreview: COMPLETE failures=0'){throw "Preview failed: $taskLog"}
    Write-Output "Ammo readout $taskWidth PASS exit=0 (live plus six rendering fixtures)"
}
