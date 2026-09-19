param([int[]]$Widths=@(1280,960))
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$outputDirectory=Join-Path $projectRoot 'Saved/EnhancementAudit'
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$runId=Get-Date -Format 'yyyyMMddHHmmss'
foreach($width in $Widths){
    foreach($phase in @('write','reload')){
        $logPath=Join-Path $outputDirectory "$runId-$width-$phase.log"
        $loadSwitch=if($phase -eq 'reload'){' -EnhancementLoadAudit'}else{''}
        $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -ColdSteelEnhancementAudit -ColdSteelProfile=EnhancementAudit_{3}_{1} -abslog="{4}"{5}' -f $projectRoot,$width,([int]($width*9/16)),$runId,$logPath,$loadSwitch
        $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
        if(!$audit.WaitForExit(180000)){$audit.Kill();throw "Owned enhancement audit timed out: $logPath"}
        $log=[IO.File]::ReadAllText($logPath)
        if($audit.ExitCode -ne 0 -or $log -notmatch 'Enhancement: COMPLETE checks=\d+ failures=0' -or $log -match 'Enhancement: FAIL'){throw "Enhancement audit failed: $logPath (exit $($audit.ExitCode))"}
        Write-Output "PASS $width $phase : $logPath"
    }
}
