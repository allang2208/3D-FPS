param([ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='baseline',[string]$Only='')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/SourceAssets/HumanoidHitVolume20261018"
if(Test-Path -LiteralPath "$taskOut/$Label.json"){Write-Output "Preserving existing report: $Label.json"; return}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(1800))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch busy; no probe started.'}
    Write-Output 'Read-only UE query batch acquired; waiting only for Editor module writes.'
    $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor'})
    foreach($taskBuild in $taskBuilds){
        try{[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()}catch [ArgumentException]{}
    }
    $taskFilter=@(); if($Only){$taskFilter+="-Only=$Only"}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=HumanoidHitVolumeAudit "-Report=$taskOut/$Label.json" @taskFilter -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$taskOut/CommandletUser/" "-abslog=$taskOut/Logs/$Label.log" *> "$taskOut/Logs/$Label-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;only=$Only;gameplay_started=$false;assets_saved=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOut/$($Label)_exit.json" -Encoding utf8
    if($taskExit -ne 0){throw "Humanoid hit-volume audit exit $taskExit; see Logs/$Label.log"}
    Write-Output 'Humanoid hit-volume audit completed.'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
