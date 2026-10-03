param([string]$ProjectRoot = 'D:/FPS3D/FPSGAME', [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$taskReceiptPath = Join-Path $PSScriptRoot 'Receipts/delivery.json'
$taskReceipt = @{ status = 'Prepared'; runtime_tested = $false; editor_gui_or_game_launched = $false; targets = @{} }
function Save-TaskReceipt {
    $taskReceipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
}
function Wait-BackgroundWindow {
    $taskDeadline = [DateTime]::UtcNow.AddMinutes(20)
    while ($true) {
        $taskProcesses = @(Get-CimInstance Win32_Process)
        $taskGui = @($taskProcesses | Where-Object {
            $_.Name -eq 'UnrealEditor.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')
        })
        if ($taskGui.Count) { throw 'FPSGAME GUI editor is using the native DLL; save and close it before the ordinary build. No process was stopped.' }
        $taskBusy = @($taskProcesses | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe', 'cl.exe', 'link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject'))
        })
        if ($taskBusy.Count -eq 0) { return }
        if ([DateTime]::UtcNow -ge $taskDeadline) { throw 'Existing build/asset commandlet window did not release. No process was stopped.' }
        Start-Sleep -Seconds 5
    }
}
Save-TaskReceipt
try {
    $taskReceipt.status = 'WaitingForAssetWindow'; Save-TaskReceipt
    Wait-BackgroundWindow
    $taskAssetMutex = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
    $taskOwnsMutex = $false
    try {
        try { $taskOwnsMutex = $taskAssetMutex.WaitOne([TimeSpan]::FromMinutes(10)) }
        catch [Threading.AbandonedMutexException] { $taskOwnsMutex = $true }
        if (-not $taskOwnsMutex) { throw 'Asset batch mutex did not become available; no request was sent.' }
        Wait-BackgroundWindow
        $taskReceipt.status = 'AuthoringStaffCollision'; Save-TaskReceipt
        $taskAssetLog = Join-Path $PSScriptRoot 'Receipts/asset-commandlet.log'
        $taskArguments = @(
            "$ProjectRoot/FPSGAME.uproject", '-run=pythonscript',
            "-script=$PSScriptRoot/prepare_staff_physics.py", '-unattended', '-nop4',
            '-nosplash', '-nosound', '-nullrhi', "-abslog=$taskAssetLog"
        )
        & "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" @taskArguments > (Join-Path $PSScriptRoot 'Receipts/asset-console.log') 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Staff authoring commandlet failed: $LASTEXITCODE; see $taskAssetLog" }
        $taskAssets = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Receipts/assets.json') -Raw | ConvertFrom-Json
        if (-not $taskAssets.saved) { throw 'Staff asset save did not complete' }
        $taskReceipt.assets = $taskAssets; Save-TaskReceipt
    } finally {
        if ($taskOwnsMutex) { $taskAssetMutex.ReleaseMutex() }
        $taskAssetMutex.Dispose()
    }
    foreach ($taskTarget in @('FPSGAME', 'FPSGAMEEditor')) {
        $taskReceipt.status = "WaitingFor$taskTarget"; Save-TaskReceipt
        Wait-BackgroundWindow
        $taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $taskConsole = Join-Path $PSScriptRoot "Receipts/$taskTarget-$taskStamp.console.log"
        $taskReceipt.status = "Building$taskTarget"; Save-TaskReceipt
        if ($taskTarget -eq 'FPSGAMEEditor') {
            & "$ProjectRoot/Tools/Build/Build-Editor.ps1" -EngineRoot $EngineRoot > $taskConsole 2>&1
            $taskLogLine = Get-Content -LiteralPath $taskConsole -Tail 6 | Where-Object { $_ -match 'Runtime testing remains manual\. Log: (.+)$' } | Select-Object -Last 1
            if ($taskLogLine -match 'Log: (.+)$') { $taskBuildLog = $Matches[1].Trim() }
        } else {
            $taskBuildLog = "$ProjectRoot/Saved/BuildGame/witch-staff-drop-$taskStamp.log"
            & "$EngineRoot/Engine/Build/BatchFiles/Build.bat" FPSGAME Win64 Development "-Project=$ProjectRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$taskBuildLog" > $taskConsole 2>&1
            if ($LASTEXITCODE -ne 0) { throw "Game build failed: $LASTEXITCODE; see $taskBuildLog" }
        }
        $taskReceipt.targets[$taskTarget] = @{ status = 'Succeeded'; log = $taskBuildLog }
        Save-TaskReceipt
    }
    $taskReceipt.status = 'StaffAssetsSavedAndOrdinaryEditorGameBuildsCompleted'
    $taskReceipt.completed_utc = [DateTime]::UtcNow.ToString('o')
    Save-TaskReceipt
    Write-Output 'Witch staff physics assets saved; ordinary Game and Editor builds completed. No runtime testing or GUI launch.'
} catch {
    $taskReceipt.status = 'FailedOrBlocked'
    $taskReceipt.error = $_.Exception.Message
    Save-TaskReceipt
    throw
}
