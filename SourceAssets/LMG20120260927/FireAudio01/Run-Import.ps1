param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Log)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(300000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'Asset authoring window is busy; no commandlet was started.' }
    $taskDeadline = [DateTime]::UtcNow.AddMinutes(5)
    do {
        $taskProcesses = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject' })
        if ($taskProcesses | Where-Object Name -eq 'UnrealEditor.exe') { throw 'FPSGAME GUI is active; use its existing MCP bridge.' }
        $taskPending = @($taskProcesses | Where-Object Name -eq 'UnrealEditor-Cmd.exe')
        if ($taskPending.Count -eq 0) { break }
        if ([DateTime]::UtcNow -ge $taskDeadline) { throw 'Existing background importer is still active; this import was not started.' }
        foreach ($taskProcess in $taskPending) { Wait-Process -Id $taskProcess.ProcessId -Timeout 15 -ErrorAction SilentlyContinue }
    } while ($true)
    $scriptPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $Script))
    $logPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $Log))
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$scriptPath" `
        -unattended -nop4 -nosplash -nosound -NullRHI -NoLiveCoding "-abslog=$logPath"
    if ($LASTEXITCODE -ne 0) { throw "Asset authoring failed ($LASTEXITCODE); see $logPath" }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
