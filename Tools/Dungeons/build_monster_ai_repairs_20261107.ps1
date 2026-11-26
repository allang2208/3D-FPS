param([string[]]$Targets=@('FPSGAMEEditor'),[string]$ReceiptFolder='DungeonMonsterAIRepairs20261107',[switch]$UseGameIfEditorOpen)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path (Join-Path $taskProject 'SourceAssets') $ReceiptFolder
[IO.Directory]::CreateDirectory($taskOutput) | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    Write-Output 'Dungeon monster AI repairs: waiting for current UE batch/build.'
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    foreach ($taskTarget in $Targets) {
        while ($true) {
            $taskProcesses=@(Get-CimInstance Win32_Process)
            $taskEditor=@($taskProcesses | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME'})
            $taskBusy=@($taskProcesses | Where-Object {
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
                $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')
            })
            if (-not $taskBusy.Count) {
                if ($taskEditor.Count -and $taskTarget -eq 'FPSGAMEEditor') {
                    if (-not $UseGameIfEditorOpen) {throw 'Save and close the FPSGAME editor before the native build. No process was stopped.'}
                    $taskTarget='FPSGAME'
                    Write-Output 'Editor DLL is in use. Building the standalone Game target without touching that DLL.'
                }
                if ($taskTarget -eq 'FPSGAME' -and @($taskProcesses | Where-Object {$_.Name -eq 'FPSGAME.exe'}).Count) {throw 'The standalone FPSGAME executable is in use. No process was stopped.'}
                break
            }
            foreach ($taskItem in $taskBusy) {
                $taskProcess=Get-Process -Id $taskItem.ProcessId -ErrorAction SilentlyContinue
                if ($taskProcess) {[void]$taskProcess.WaitForExit(5000)}
            }
        }
        $taskMode=@()
        $taskDefinition=Join-Path $taskProject "Intermediate/Build/Win64/x64/$taskTarget/Development/Core/SharedDefinitions.Core.Cpp20.h"
        if ((Test-Path -LiteralPath $taskDefinition) -and [IO.File]::ReadAllText($taskDefinition) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$') {$taskMode+='-NoLiveCoding'}
        $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
        $taskLog=Join-Path $taskOutput "build-$taskTarget-$taskStamp.log"
        $taskStdout=Join-Path $taskOutput "stdout-$taskTarget-$taskStamp.log"
        Write-Output "DUNGEON_AI_BUILD_STARTED target=$taskTarget log=$taskLog"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReloadFromIDE @taskMode -MaxParallelActions=4 "-Log=$taskLog" *> $taskStdout
        $taskCode=$LASTEXITCODE
        @{target=$taskTarget;exit_code=$taskCode;log=$taskLog;runtime_tested=$false;editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput "build-$taskTarget.json") -Encoding utf8
        Write-Output "DUNGEON_AI_BUILD_EXIT=$taskCode target=$taskTarget log=$taskLog"
        if ($taskCode -ne 0) {throw "Build failed: $taskLog"}
    }
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
