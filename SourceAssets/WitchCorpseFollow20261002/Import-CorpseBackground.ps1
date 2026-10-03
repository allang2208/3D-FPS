$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME/SourceAssets/WitchCorpseFollow20261002'
$taskProject = 'D:/FPS3D/FPSGAME/FPSGAME.uproject'
$taskCmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$taskScript = Join-Path $taskRoot 'import_corpse_mesh.py'
$taskLog = Join-Path $taskRoot ('import-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskGateHeld = $false
try {
    try { $taskGateHeld = $taskGate.WaitOne([TimeSpan]::FromMinutes(5)) }
    catch [Threading.AbandonedMutexException] {
        $taskGateHeld = $true
        throw 'Previous UE asset batch ended unexpectedly; import not started.'
    }
    if (-not $taskGateHeld) { throw 'UE asset batch remains busy; import not started.' }
    $taskDeadline = [DateTime]::UtcNow.AddMinutes(10)
    do {
        $taskProcesses = @(Get-CimInstance Win32_Process)
        $taskEditor = @($taskProcesses | Where-Object {
            $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME'
        })
        if ($taskEditor.Count -gt 0) { throw 'FPSGAME editor is open; preserve loaded assets and retry after it closes.' }
        $taskBusy = @($taskProcesses | Where-Object {
            $_.Name -match '^(UnrealBuildTool|cl|link)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')
        })
        if ($taskBusy.Count -eq 0) { break }
        if ([DateTime]::UtcNow -ge $taskDeadline) { throw 'Native build or commandlet remains busy; import not started.' }
        Start-Sleep -Seconds 5
    } while ($true)
    $taskArguments = '"' + $taskProject + '" -run=pythonscript -script="' + $taskScript +
        '" -unattended -nop4 -nosplash -nosound -nullrhi -multiprocess -DDC=InstalledNoZenLocalFallback -abslog="' + $taskLog + '"'
    $taskProcess = Start-Process -FilePath $taskCmd -ArgumentList $taskArguments -WindowStyle Hidden -PassThru
    Write-Output ('Background corpse import PID: ' + $taskProcess.Id)
    Write-Output ('Import log: ' + $taskLog)
    $taskProcess.WaitForExit()
    $taskReceipt = [ordered]@{
        commandlet_exit_code = $taskProcess.ExitCode
        import_log = $taskLog
        completed_utc = [DateTime]::UtcNow.ToString('o')
    }
    $taskReceipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'import-commandlet.json') -Encoding UTF8
    if ($taskProcess.ExitCode -ne 0) { throw ('Corpse import failed with exit code ' + $taskProcess.ExitCode + '; log: ' + $taskLog) }
    if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'assets.json'))) { throw 'Commandlet ended without the asset-save receipt.' }
    Write-Output 'Corpse skeletal mesh and Physics Asset import/save completed. Runtime testing remains manual.'
} finally {
    if ($taskGateHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
