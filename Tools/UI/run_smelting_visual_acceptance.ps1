# 冶炼面板视觉审计（先例：run_inventory_visual_acceptance.ps1）。
# 独立 -game 进程 + 隔离档（-ColdSteelProfile 同时隔离角色档与体素世界档），
# 自动放炉、配料、起炉，四态各截一屏到 Saved/SmeltingVisual/，跑完自动退出。
param([int[]]$Widths=@(2560,1280),[int]$TimeoutSeconds=240)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runId=Get-Date -Format 'yyyyMMddHHmmss'
New-Item -ItemType Directory -Force -Path "$projectRoot/Saved/SmeltingVisual" | Out-Null
foreach($width in $Widths){
    $height=[int]($width*9/16);$logPath="$projectRoot/Saved/SmeltingVisual/$runId-$width.log"
    # 本机 GTX 750 Ti／32GB：1920 直跑会在 PSO/着色器预热时把虚拟内存顶到 ~22GB 触发页面文件 OOM
    # （GenericPlatformMemory.cpp:300）。审计用 1280 降载即可跑到截图相位；
    # 注意勿加 -ExecCmds="...;..." 之类内嵌引号参数——实测会让 UE 早退、连 -abslog 都不写。
    $arguments='"{0}/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -windowed -ResX={1} -ResY={2} -ForceRes -unattended -nosound -NoSplash -CpuCount=2 -SmeltingVisualAudit -ColdSteelProfile=SmeltingVisualAudit_{3}_{1} -abslog="{4}"' -f $projectRoot,$width,$height,$runId,$logPath
    $audit=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    if(!$audit.WaitForExit($TimeoutSeconds*1000)){$audit.Kill();throw "Smelting visual audit timed out: $logPath"}
    $log=[IO.File]::ReadAllText($logPath)
    if($log -notmatch 'SmeltingVisualAudit: COMPLETE checks=\d+ failures=0' -or $log -match 'SmeltingVisualAudit: FAIL'){
        Write-Output "AUDIT DID NOT PASS cleanly (截图可能仍已生成，先查图再重跑): $logPath (exit $($audit.ExitCode))"; continue}
    Write-Output "PASS $width x $height : $logPath"
}
Get-ChildItem "$projectRoot/Saved/SmeltingVisual" -Filter "$runId*"
