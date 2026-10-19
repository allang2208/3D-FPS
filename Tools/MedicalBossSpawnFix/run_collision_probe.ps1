$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/SourceAssets/MedicalBossSpawnFix20261018"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch busy; no probe started.'}
    $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'})
    foreach($taskBuild in $taskBuilds){
        try{[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()}catch [ArgumentException]{}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=MedicalBossSpawnDiagnosis "-Module=$taskOut/theatre_module.json" "-Report=$taskOut/collision_probe.json" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$taskOut/CommandletUser/" "-abslog=$taskOut/Logs/collision-probe.log" *> "$taskOut/Logs/collision-probe-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;gameplay_started=$false;assets_saved=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOut/collision_probe_exit.json" -Encoding utf8
    if($taskExit -ne 0){throw "Collision probe exit $taskExit; see collision-probe.log"}
    Write-Output 'Collision probe completed.'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
