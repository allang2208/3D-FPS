param()
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskScript=Join-Path $taskProject 'Tools/MonsterAI/audit_runtime_geometry.py'
$taskOutput=Join-Path $taskProject 'Saved/MonsterGeometryAudit20261006'
[IO.Directory]::CreateDirectory($taskOutput) | Out-Null
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskDeadline=[DateTime]::UtcNow.AddMinutes(20)
try {
    while(-not $taskHeld) {
        if([DateTime]::UtcNow -gt $taskDeadline){throw 'Read window remained occupied; no process was stopped.'}
        $taskProcesses=@(Get-CimInstance Win32_Process)
        $taskGUI=@($taskProcesses|Where-Object {$_.Name -eq 'UnrealEditor.exe' -and ($_.CommandLine -match 'FPSGAME' -or [string]::IsNullOrWhiteSpace($_.CommandLine))})
        if($taskGUI.Count) {
            & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript -OutputFile (Join-Path $taskOutput "read-bridge-$taskStamp.txt") -MaxOutputChars 3500 -QueueWaitSeconds 120
            if($LASTEXITCODE -ne 0){throw 'Read-only bridge request did not complete; preserve its result.'}
            exit 0
        }
        $taskBusy=@($taskProcesses|Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')})
        if($taskBusy.Count){Start-Sleep -Seconds 5;continue}
        try {$taskHeld=$taskGate.WaitOne(1000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    }
    if(@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')}).Count){throw 'An editor started before the read window; audit not started.'}
    $taskLog=Join-Path $taskOutput "read-commandlet-$taskStamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosound -NullRHI -NoSplash "-abslog=$taskLog" *> (Join-Path $taskOutput "read-console-$taskStamp.log")
    if($LASTEXITCODE -ne 0){throw "Audit commandlet failed: $taskLog"}
    $taskReport=Get-Content (Join-Path $taskOutput 'runtime.json') -Raw | ConvertFrom-Json
    if(-not $taskReport.complete){throw 'Read-only audit did not finish.'}
    Write-Output "Geometry audit finished; actor errors=$($taskReport.errors.Count). $taskLog"
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
