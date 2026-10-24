param([int]$MaximumWaitSeconds=1800)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskProjectPattern='(?i)D:[\\/]FPS3D[\\/]FPSGAME[\\/]FPSGAME\.uproject(?:["\s]|$)'
$taskOutput="$taskRoot/SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV7"
$taskDeadline=[DateTime]::UtcNow.AddSeconds($MaximumWaitSeconds)
do {
    $taskProcesses=@(Get-CimInstance Win32_Process)
    if($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match $taskProjectPattern}) {throw 'Preserving the open editor; native DLL update requires editor exit.'}
    $taskOwners=@($taskProcesses | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match $taskProjectPattern)})
    if(-not $taskOwners.Count){break}
    if([DateTime]::UtcNow -gt $taskDeadline){throw 'Existing build/cook still owns binaries; nothing interrupted.'}
    Start-Sleep -Seconds 8
} while($true)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch remains occupied; build not started.'}
    foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
        $taskOwners=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match $taskProjectPattern) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if($taskOwners.Count){throw 'Preserving a new binary owner; build not started.'}
        $taskOptions=@()
        $taskDefinitions="$taskRoot/Intermediate/Build/Win64/x64/$taskTarget/Development/Core/SharedDefinitions.Core.Cpp20.h"
        if((Test-Path -LiteralPath $taskDefinitions) -and [IO.File]::ReadAllText($taskDefinitions) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$taskOptions+='-NoLiveCoding'}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE @taskOptions -MaxParallelActions=4 "-Log=$taskOutput/build-$taskTarget.log" *> "$taskOutput/build-$taskTarget-console.log"
        $taskExit=$LASTEXITCODE
        @{target=$taskTarget;exit_code=$taskExit;game_run=$false;editor_opened=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/build-$taskTarget.json" -Encoding utf8
        if($taskExit -ne 0){throw "Build failed: $taskTarget"}
        Write-Output "$taskTarget saved."
    }
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
