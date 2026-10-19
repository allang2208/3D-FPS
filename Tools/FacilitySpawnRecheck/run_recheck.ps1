param([int]$Seed=1327166464,[ValidatePattern('^[a-zA-Z0-9_-]+$')][string]$Label='recheck')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/SourceAssets/FacilitySpawnRecheck20261018"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch busy; no probe started.'}
    Write-Output 'Read-only UE query batch acquired; waiting only for Editor module writes.'
    $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor'})
    foreach($taskBuild in $taskBuilds){
        try{[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()}catch [ArgumentException]{}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=FacilitySpawnRecheck "-Report=$taskOut/$Label.json" "-Seed=$Seed" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$taskOut/CommandletUser/" "-abslog=$taskOut/Logs/$Label.log" *> "$taskOut/Logs/$Label-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;seed=$Seed;gameplay_started=$false;assets_saved=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOut/$($Label)_exit.json" -Encoding utf8
    if($taskExit -ne 0){throw "Spawn recheck exit $taskExit; see recheck.log"}
    Copy-Item -LiteralPath "$taskOut/manifest.json" -Destination "$taskOut/$Label-manifest.json"
    Write-Output 'Spawn recheck completed.'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
