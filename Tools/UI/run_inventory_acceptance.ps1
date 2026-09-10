param([string]$Editor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',[int[]]$Widths=@(1280,960,1920))
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$outputDirectory=Join-Path $projectRoot 'Saved/InventoryMigration'
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$runId=Get-Date -Format 'yyyyMMddHHmmss'
foreach($dimensions in @(@(1280,720),@(960,540),@(1920,1080))) {
    $width=$dimensions[0];$height=$dimensions[1]
    if($width -notin $Widths){continue}
    $profileName="InventoryAudit_$($runId)_$width"
    foreach($phase in @('write','reload')) {
        $logPath=Join-Path $outputDirectory "$runId-$width-$phase.log"
        $loadSwitch=if($phase -eq 'reload'){' -ColdSteelInventoryLoadAudit'}else{''}
        $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -ColdSteelInventoryAudit -ColdSteelProfile={3} -abslog="{4}"{5}' -f $projectRoot,$width,$height,$profileName,$logPath,$loadSwitch
        $auditProcess=Start-Process -FilePath $Editor -ArgumentList $arguments -WindowStyle Hidden -PassThru
        if(!$auditProcess.WaitForExit(180000)){$auditProcess.Kill();throw "Owned inventory audit timed out: $logPath"}
        if($auditProcess.ExitCode -ne 0){throw "Runtime failed: $width x $height $phase, exit $($auditProcess.ExitCode)"}
        $log=[IO.File]::ReadAllText($logPath)
        if($log -notmatch 'ColdSteelInventory: COMPLETE checks=\d+ failures=0' -or $log -match 'ColdSteelInventory: FAIL'){throw "Inventory audit failed: $logPath"}
        Write-Output "PASS $width x $height $phase : $logPath"
    }
}
