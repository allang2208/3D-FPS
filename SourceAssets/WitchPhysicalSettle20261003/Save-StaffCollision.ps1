param([string]$ProjectRoot = 'D:/FPS3D/FPSGAME', [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$taskReceiptPath = Join-Path $PSScriptRoot 'Receipts/delivery.json'
function Set-AssetStatus([string]$Status) {
    $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
    $taskReceipt['asset_changes_required'] = $true
    $taskReceipt['asset_status'] = $Status
    $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
}
function Wait-AssetWindow {
    $taskDeadline = [DateTime]::UtcNow.AddMinutes(15)
    while ($true) {
        $taskProcesses = @(Get-CimInstance Win32_Process)
        $taskGui = @($taskProcesses | Where-Object {
            $_.Name -eq 'UnrealEditor.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')
        })
        if ($taskGui.Count) { throw 'FPSGAME editor is running. Keep its loaded assets intact; use the shared bridge instead.' }
        $taskBusy = @($taskProcesses | Where-Object {
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')) -or
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if (-not $taskBusy.Count) { return }
        if ([DateTime]::UtcNow -ge $taskDeadline) { throw 'Existing build/commandlet window did not release. No process was stopped.' }
        Start-Sleep -Seconds 5
    }
}
Set-AssetStatus 'WaitingForCommandletWindow'
$taskMutex = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskOwnsMutex = $false
try {
    Wait-AssetWindow
    try { $taskOwnsMutex = $taskMutex.WaitOne([TimeSpan]::FromMinutes(5)) }
    catch [Threading.AbandonedMutexException] { $taskOwnsMutex = $true }
    if (-not $taskOwnsMutex) { throw 'Asset batch mutex did not become available.' }
    Wait-AssetWindow
    Set-AssetStatus 'AuthoringCompleteStaffCollision'
    $taskStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog = Join-Path $PSScriptRoot "Receipts/staff-collision-commandlet-$taskStamp.log"
    $taskConsole = Join-Path $PSScriptRoot "Receipts/staff-collision-console-$taskStamp.log"
    $taskArguments = @(
        "$ProjectRoot/FPSGAME.uproject", '-run=pythonscript',
        "-script=$PSScriptRoot/prepare_staff_collision.py", '-unattended', '-nop4',
        '-nosplash', '-nosound', '-nullrhi', "-abslog=$taskLog"
    )
    & "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" @taskArguments > $taskConsole 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Staff collision commandlet failed: $LASTEXITCODE; log $taskLog" }
    $taskAssets = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Receipts/staff-collision.json') -Raw | ConvertFrom-Json -AsHashtable
    if (-not $taskAssets.saved) { throw 'Staff collision save did not complete.' }
    $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
    $taskReceipt['assets'] = $taskAssets
    $taskReceipt['asset_status'] = 'Saved'
    $taskReceipt['asset_commandlet_log'] = $taskLog
    $null = $taskReceipt.Remove('asset_error')
    $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
    Write-Output 'Complete staff collision saved. No GUI or game launch; no runtime test.'
} catch {
    $taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json -AsHashtable
    $taskReceipt['asset_status'] = 'FailedOrBlocked'
    $taskReceipt['asset_error'] = $_.Exception.Message
    $taskReceipt | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $taskReceiptPath -Encoding utf8
    throw
} finally {
    if ($taskOwnsMutex) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
