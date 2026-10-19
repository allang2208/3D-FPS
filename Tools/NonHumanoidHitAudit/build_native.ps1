param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'),[int]$MaximumWaitSeconds=600,[int]$MaxParallelActions=4,[switch]$UseDefaultLiveCodingSupport)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOutput=if($env:MONSTER_AUDIT_OUTPUT){$env:MONSTER_AUDIT_OUTPUT}else{"$taskRoot/SourceAssets/NonHumanoidHitAudit20261018"}
function Get-TaskEditorOwners($taskProcesses) {
    foreach($taskProcess in $taskProcesses | Where-Object {$_.Name -match '^UnrealEditor(-Cmd)?\.exe$'}) {
        $taskLoaded=@((Get-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue).Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-FPSGAME.dll'})
        if($taskLoaded.Count) {
            if($taskLoaded[0].FileName.Replace('\','/') -eq "$taskRoot/Binaries/Win64/UnrealEditor-FPSGAME.dll") {$taskProcess}
        } elseif($taskProcess.CommandLine -match 'D:[/\\]FPS3D[/\\]FPSGAME[/\\]FPSGAME\.uproject') {$taskProcess}
    }
}
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
            $taskOwners=@(Get-TaskEditorOwners $taskProcesses)
        }else{
            $taskOwners=@($taskProcesses | Where-Object {$_.Name -match '^FPSGAME(-Win64-.+)?\.exe$'})
        }
        $taskOwnerDeadline=[DateTime]::UtcNow.AddMinutes(10)
        while($taskOwners.Count){
            if([DateTime]::UtcNow -gt $taskOwnerDeadline){throw "Preserving the running binary owner; cannot write $taskTarget."}
            Start-Sleep -Seconds 5
            $taskProcesses=@(Get-CimInstance Win32_Process)
            if($taskTarget -eq 'FPSGAMEEditor'){$taskOwners=@(Get-TaskEditorOwners $taskProcesses)}
            else{$taskOwners=@($taskProcesses | Where-Object {$_.Name -match '^FPSGAME(-Win64-.+)?\.exe$'})}
        }
        $taskModes=@()
        $taskDefinitions="$taskRoot/Intermediate/Build/Win64/x64/$taskTarget/Development/Core/SharedDefinitions.Core.Cpp20.h"
        if((-not $UseDefaultLiveCodingSupport) -and (Test-Path -LiteralPath $taskDefinitions) -and [IO.File]::ReadAllText($taskDefinitions) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$taskModes+='-NoLiveCoding'}
        $taskLog="$taskOutput/Logs/build-$taskTarget.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE @taskModes "-MaxParallelActions=$MaxParallelActions" "-Log=$taskLog" *> "$taskOutput/Logs/build-$taskTarget-stdout.log"
        $taskExit=$LASTEXITCODE
        @{target=$taskTarget;exit_code=$taskExit;log=$taskLog;runtime_tested=$false;editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/build-$taskTarget.json" -Encoding utf8
        if($taskExit -ne 0){throw "Build failed: $taskLog"}
        Write-Output "$taskTarget build succeeded."
    }
}finally{
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
