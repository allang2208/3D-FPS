param([int]$Width=1920,[int]$Height=1080)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$outputDirectory=Join-Path $projectRoot 'Saved/EnhancementUIUpgrade20260913/preview'
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$runId=Get-Date -Format 'yyyyMMddHHmmss'
$logPath=Join-Path $outputDirectory "preview-$runId.log"
$arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -RenderOffscreen -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -NoScreenMessages -ColdSteelEnhancementAudit -EnhancementUIPreview -ColdSteelProfile=EnhancementPreview_{3} -ExecCmds="t.MaxFPS 30" -abslog="{4}"' -f $projectRoot,$Width,$Height,$runId,$logPath
$previewProcess=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
$started=Get-Date
while(!$previewProcess.WaitForExit(1000)){
    if(((Get-Date)-$started).TotalSeconds -gt 180){$previewProcess.Kill();throw "Preview process timed out: $logPath"}
}
$log=[IO.File]::ReadAllText($logPath)
if($previewProcess.ExitCode -ne 0 -or $log -notmatch 'EnhancementPreview: COMPLETE'){throw "Preview did not finish: $logPath"}
foreach($page in 'enhance','enchant'){
    $file=Get-Item -LiteralPath (Join-Path $outputDirectory "$page-$Width.png")
    if($file.LastWriteTime -lt $started){throw "Preview file was not refreshed: $($file.FullName)"}
    Write-Output $file.FullName
}
