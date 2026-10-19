param([string]$Only='', [ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='install',[int]$Revision=1)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/SourceAssets/HumanoidHitRepair20261018"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE asset batch occupied; authoring has not started.'}
    $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
    foreach($taskBuild in $taskBuilds){try{[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()}catch [ArgumentException]{}}
    $taskEditors=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME'})
    if($taskEditors.Count){throw 'Preserving the open editor and loaded assets; no background package writes started.'}
    $taskFilter=@();if($Only){$taskFilter+="-Only=$Only"}
    Write-Output 'Authoring per-model hit geometry and saving packages; no gameplay or tests.'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=HumanoidHitVolumeAuthoring "-Report=$taskOut/$Label.json" "-Revision=$Revision" @taskFilter -unattended -nop4 -nosplash -nullrhi -nosound -NoLiveCoding "-abslog=$taskOut/Logs/$Label.log" *> "$taskOut/Logs/$Label-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;only=$Only;report="$taskOut/$Label.json";gameplay_started=$false;tests_run=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOut/$($Label)_exit.json" -Encoding utf8
    if($taskExit -ne 0){throw "Authoring exit $taskExit; inspect the saved partial receipt before resuming."}
    Write-Output 'Per-model hit assets saved.'
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
