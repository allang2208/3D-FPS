param([string]$ProjectRoot = 'D:/FPS3D/FPSGAME', [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8', [ValidateSet('Both','Editor','Game')][string]$Mode = 'Both')
$ErrorActionPreference = 'Stop'
$taskReceiptPath = Join-Path $PSScriptRoot 'delivery.json'

function Wait-BuildWindow([bool]$ForEditor) {
    $taskDeadline = [DateTime]::UtcNow.AddMinutes(10)
    while ($true) {
        $taskProcesses = @(Get-CimInstance Win32_Process)
        if ($ForEditor) {
            $taskEditors = @($taskProcesses | Where-Object {
                $_.Name -eq 'UnrealEditor.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')
            })
            if ($taskEditors.Count -gt 0) { throw 'Save and close the FPSGAME editor before the ordinary Editor build. No process was stopped.' }
        }
        $taskBusy = @($taskProcesses | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($ForEditor -and $_.Name -eq 'UnrealEditor-Cmd.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject'))
        })
        if ($taskBusy.Count -eq 0) { return }
        if ([DateTime]::UtcNow -ge $taskDeadline) { throw 'Existing build/commandlet window did not release. No process was stopped.' }
        Start-Sleep -Seconds 5
    }
}

$taskTargets = if ($Mode -eq 'Game') { @('FPSGAME') } elseif ($Mode -eq 'Editor') { @('FPSGAMEEditor') } else { @('FPSGAMEEditor','FPSGAME') }
foreach ($taskTarget in $taskTargets) {
    $taskForEditor = $taskTarget -eq 'FPSGAMEEditor'
    $taskKey = "$taskTarget Win64 Development"
    $taskPrefix = if ($taskForEditor) { 'editor' } else { 'game' }
    $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
    $taskReceipt.targets[$taskKey] = 'WaitingForBuildWindow'
    $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
    try {
        Wait-BuildWindow $taskForEditor
        $taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $taskConsole = Join-Path $PSScriptRoot ("build-$taskPrefix-console-$taskStamp.log")
        $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
        $taskReceipt.targets[$taskKey] = 'Building'
        $taskReceipt["${taskPrefix}_build_started_utc"] = [DateTime]::UtcNow.ToString('o')
        $taskReceipt["${taskPrefix}_console_log"] = $taskConsole
        $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
        if ($taskForEditor) {
            & (Join-Path $ProjectRoot 'Tools/Build/Build-Editor.ps1') -EngineRoot $EngineRoot 2>&1 | Tee-Object -FilePath $taskConsole
            $taskLogLine = Get-Content -LiteralPath $taskConsole -Tail 5 | Where-Object { $_ -match 'Runtime testing remains manual\. Log: (.+)$' } | Select-Object -Last 1
            if ($taskLogLine -match 'Log: (.+)$') { $taskBuildLog = $Matches[1].Trim() }
        } else {
            $taskBuildLog = Join-Path $ProjectRoot ("Saved/BuildGame/witch-corpse-follow-$taskStamp.log")
            & (Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat') FPSGAME Win64 Development "-Project=$ProjectRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$taskBuildLog" 2>&1 | Tee-Object -FilePath $taskConsole
            if ($LASTEXITCODE -ne 0) { throw "Game build failed with exit code $LASTEXITCODE; log $taskBuildLog" }
        }
        $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
        $taskReceipt.targets[$taskKey] = 'Succeeded'
        $taskReceipt["${taskPrefix}_build_completed_utc"] = [DateTime]::UtcNow.ToString('o')
        $taskReceipt["${taskPrefix}_build_exit_code"] = 0
        $taskReceipt["${taskPrefix}_build_log"] = $taskBuildLog
        $null = $taskReceipt.Remove("${taskPrefix}_build_error")
        $taskTimeLine = Get-Content -LiteralPath $taskBuildLog -Tail 12 | Where-Object { $_ -match 'Total execution time: ([0-9.]+) seconds' } | Select-Object -Last 1
        if ($taskTimeLine -match 'Total execution time: ([0-9.]+) seconds') { $taskReceipt["${taskPrefix}_build_seconds"] = [double]$Matches[1] }
        $taskBinary = Get-Item (Join-Path $ProjectRoot $(if ($taskForEditor) { 'Binaries/Win64/UnrealEditor-FPSGAME.dll' } else { 'Binaries/Win64/FPSGAME.exe' }))
        $taskReceipt["${taskPrefix}_binary"] = $taskBinary.FullName
        $taskReceipt["${taskPrefix}_binary_written_utc"] = $taskBinary.LastWriteTimeUtc.ToString('o')
        if ($taskForEditor) { $taskReceipt['editor_dll'] = $taskBinary.FullName; $taskReceipt['editor_dll_written_utc'] = $taskBinary.LastWriteTimeUtc.ToString('o') }
        $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
    } catch {
        $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
        $taskReceipt.targets[$taskKey] = 'FailedOrBlocked'
        $taskReceipt["${taskPrefix}_build_error"] = $_.Exception.Message
        $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
        throw
    }
}
$taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
if ($taskReceipt.targets['FPSGAMEEditor Win64 Development'] -eq 'Succeeded' -and $taskReceipt.targets['FPSGAME Win64 Development'] -eq 'Succeeded') {
    $taskReceipt['status'] = 'SourceIntegratedOrdinaryEditorAndGameBuildsCompleted'
    $taskReceipt['completed_utc'] = [DateTime]::UtcNow.ToString('o')
} else {
    $taskReceipt['status'] = 'SourceIntegratedOrdinaryBuildsPending'
}
$taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
Write-Output "Requested $Mode build pass completed. Runtime testing remains with the user."
