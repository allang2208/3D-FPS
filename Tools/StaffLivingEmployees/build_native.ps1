param([string[]]$Targets=@('FPSGAME'),[int]$MaximumWaitSeconds=600)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOutput="$taskRoot/SourceAssets/StaffLivingEmployees20261017"
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds($MaximumWaitSeconds))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; no build started.'}
    foreach($taskTarget in $Targets){
        $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
        foreach($taskProcess in $taskBuilds){
            try{[Diagnostics.Process]::GetProcessById($taskProcess.ProcessId).WaitForExit()}catch [ArgumentException]{}
        }
        $taskProcesses=@(Get-CimInstance Win32_Process)
        if($taskTarget -eq 'FPSGAMEEditor'){
            $taskOwners=@($taskProcesses | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'})
        }else{
            $taskOwners=@($taskProcesses | Where-Object {$_.Name -match '^FPSGAME(-Win64-.+)?\.exe$'})
        }
        if($taskOwners.Count){throw "Preserving the running binary owner; cannot write $taskTarget."}
        $taskModes=@()
        $taskDefinitions="$taskRoot/Intermediate/Build/Win64/x64/$taskTarget/Development/Core/SharedDefinitions.Core.Cpp20.h"
        if((Test-Path -LiteralPath $taskDefinitions) -and [IO.File]::ReadAllText($taskDefinitions) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$taskModes+='-NoLiveCoding'}
        $taskLog="$taskOutput/Logs/build-$taskTarget.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE @taskModes -MaxParallelActions=4 "-Log=$taskLog" *> "$taskOutput/Logs/build-$taskTarget-stdout.log"
        $taskExit=$LASTEXITCODE
        @{target=$taskTarget;exit_code=$taskExit;log=$taskLog;runtime_tested=$false;editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/build-$taskTarget.json" -Encoding utf8
        if($taskExit -ne 0){throw "Build failed: $taskLog"}
        Write-Output "$taskTarget build succeeded."
    }
}finally{
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
