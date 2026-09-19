param([int[]]$Widths=@(1280),[switch]$Reload,[switch]$Chest,[switch]$Inventory,[string]$Run='final_a')
$taskEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$taskOut='D:/FPS3D/FPSGAME/Saved/WarehouseMigration'
foreach($taskWidth in $Widths){
    if($taskWidth -notin @(960,1280,1920)){throw 'Unsupported preview size'}
    $taskHeight=[int]($taskWidth*9/16)
    $taskProfile="WarehouseAudit_${Run}_${taskWidth}"
    $taskMode=if($Reload){'reload'}elseif($Chest){'chest'}else{'write'}
    $taskLog="$taskOut/${Run}-${taskWidth}-${taskMode}.log"
    $taskArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','/Game/GameMaps/DayNight_Lighting','-game','-windowed',"-ResX=$taskWidth","-ResY=$taskHeight",'-ForceRes','-unattended','-nosound','-NoSplash','-ColdSteelWarehouseAudit',"-ColdSteelProfile=$taskProfile","-abslog=$taskLog")
    if($Reload){$taskArgs+='-WarehouseLoadAudit'}
    if($Chest){$taskArgs+='-WarehouseChestPreview'}
    if($Inventory){$taskArgs=$taskArgs | Where-Object { $_ -ne '-ColdSteelWarehouseAudit' };$taskArgs+='-ColdSteelInventoryAudit'}
    $taskProcess=Start-Process -FilePath $taskEngine -ArgumentList $taskArgs -PassThru -WindowStyle Hidden
    if(-not $taskProcess.WaitForExit(60000)){
        Write-Output "Warehouse validation still running PID=$($taskProcess.Id) log=$taskLog"
        if(-not $taskProcess.WaitForExit(60000)){throw "Validation exceeded 120s; process retained PID=$($taskProcess.Id)"}
    }
    $taskContent=[IO.File]::ReadAllText($taskLog)
    $taskMatch=[regex]::Match($taskContent,'(?:WarehouseAudit|ColdSteelInventory): COMPLETE checks=\d+ failures=0|WarehousePreview: COMPLETE[^\r\n]*')
    Write-Output "$taskWidth $taskMode exit=$($taskProcess.ExitCode) $($taskMatch.Value)"
    if(-not $taskMatch.Success){throw "Validation failed; inspect $taskLog"}
}
