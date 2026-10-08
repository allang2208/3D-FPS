param()
$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskScript = Join-Path $taskProject 'Tools/SpiralPillarM14/import_bite_v21.py'
$taskOutput = Join-Path $taskProject 'Saved/M14BiteV21'
[IO.Directory]::CreateDirectory($taskOutput) | Out-Null
$taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$taskDeadline = [DateTime]::UtcNow.AddMinutes(30)
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    while (-not $taskHeld) {
        if ([DateTime]::UtcNow -gt $taskDeadline) { throw 'UE production window remained occupied; no process was stopped.' }
        $taskProcesses = @(Get-CimInstance Win32_Process)
        $taskGUI = @($taskProcesses | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and ($_.CommandLine -match 'FPSGAME' -or [string]::IsNullOrWhiteSpace($_.CommandLine)) })
        if ($taskGUI.Count) {
            & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript -QueueWaitSeconds 120 -OutputFile (Join-Path $taskOutput "import-bridge-$taskStamp.txt") -MaxOutputChars 3000
            if ($LASTEXITCODE -ne 0) { throw 'UE bridge import did not complete; see its receipt.' }
            exit 0
        }
        $taskBusy = @($taskProcesses | Where-Object { $_.Name -in @('UnrealEditor-Cmd.exe', 'UnrealBuildTool.exe', 'cl.exe', 'link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        if ($taskBusy.Count) { Start-Sleep -Seconds 5; continue }
        try { $taskHeld = $taskGate.WaitOne(1000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    }
    # Re-read the process boundary after taking the shared asset-production gate.
    $taskProcesses = @(Get-CimInstance Win32_Process)
    if (@($taskProcesses | Where-Object { $_.Name -in @('UnrealEditor.exe', 'UnrealEditor-Cmd.exe') }).Count) {
        throw 'An editor started before the import window; no asset changed.'
    }
    $taskLog = Join-Path $taskOutput "import-commandlet-$taskStamp.log"
    $taskConsole = Join-Path $taskOutput "import-console-$taskStamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosound -NullRHI -NoSplash "-abslog=$taskLog" *> $taskConsole
    $taskExit = $LASTEXITCODE
    if ($taskExit -ne 0) { throw "Import commandlet exited $taskExit; see $taskLog" }
    $taskReceipt = Get-Content (Join-Path $taskProject 'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV21/Records/ue_revision.json') -Raw | ConvertFrom-Json
    if (-not $taskReceipt.complete) { throw "Import did not finish saving; see $taskLog" }
    Write-Output "M14 V21 animation, audio and Blueprint saved. Commandlet exit=$taskExit. $taskLog"
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
