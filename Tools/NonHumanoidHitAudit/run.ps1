param([string]$Only='', [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='baseline')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/SourceAssets/NonHumanoidHitAudit20261018"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; audit not started.'}
    $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
    foreach($taskBuild in $taskBuilds){try{[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()}catch [ArgumentException]{}}
    $taskFilter=@();if($Only){$taskFilter+="-Only=$Only"}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=NonHumanoidHitAudit "-Report=$taskOut/$Label.json" @taskFilter -unattended -nop4 -nosplash -nullrhi -nosound -NoLiveCoding "-abslog=$taskOut/Logs/$Label.log" *> "$taskOut/Logs/$Label-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;only=$Only;report="$taskOut/$Label.json";map_begin_play=$false;assets_saved=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOut/$($Label)_exit.json" -Encoding utf8
    if($taskExit -ne 0){throw "Audit exit $taskExit; partial evidence retained."}
    Write-Output "Audit complete: $Label"
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
