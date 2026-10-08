param()
$ErrorActionPreference = 'Stop'
$reviewRoot = 'D:/FPS3D/FPSGAME'
$reviewOutput = Join-Path $reviewRoot 'Saved/XuanChiReview20261006'
$reviewGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$reviewHeld = $false
function Set-ReviewStatus([string]$Phase, [string]$Detail = '') {
    @{ phase=$Phase; detail=$Detail; updated_utc=[DateTime]::UtcNow.ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $reviewOutput 'build-status.json') -Encoding utf8
}
try {
    Set-ReviewStatus 'waiting'
    try { $reviewHeld = $reviewGate.WaitOne([TimeSpan]::FromMinutes(30)) }
    catch [Threading.AbandonedMutexException] { $reviewHeld = $true }
    if (-not $reviewHeld) { throw 'UE batch wait timed out; no build started.' }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
        throw 'Editor holds the native DLL. Save and close it before the background build.'
    }
    $reviewDeadline = [DateTime]::UtcNow.AddMinutes(30)
    $reviewWaiting = $false
    do {
        $reviewBusy = Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe', 'UnrealBuildTool.exe', 'cl.exe', 'link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $reviewBusy) { break }
        if (-not $reviewWaiting) { Write-Output 'Waiting for the existing native build.'; $reviewWaiting = $true }
        if ([DateTime]::UtcNow -ge $reviewDeadline) { throw 'Existing build remains active.' }
        Start-Sleep -Seconds 5
    } while ($true)
    foreach ($reviewTarget in @('FPSGAMEEditor', 'FPSGAME')) {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Editor opened; preserving its session.' }
        Write-Output "XUANCHI_REVIEW_BUILD_BEGIN $reviewTarget"
        Set-ReviewStatus 'building' $reviewTarget
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $reviewTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> (Join-Path $reviewOutput "build-$reviewTarget.log")
        if ($LASTEXITCODE -ne 0) { throw "Native build failed: $reviewTarget. See its build log." }
        Write-Output "XUANCHI_REVIEW_BUILD_SAVED $reviewTarget"
    }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Editor opened; leaving isolated audit pending.' }
    Write-Output 'XUANCHI_REVIEW_RUNE_AUDIT_BEGIN'
    Set-ReviewStatus 'auditing'
    $reviewArgs = @("$reviewRoot/FPSGAME.uproject", '-run=RuneSwordAudit', '-XuanChiRunesOnly',
        '-unattended', '-nop4', '-nosplash', '-nosound', '-NullRHI', "-abslog=$reviewOutput/rune-audit.log",
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @reviewArgs *> (Join-Path $reviewOutput 'rune-audit-console.log')
    if ($LASTEXITCODE -ne 0) { throw 'Isolated rune audit failed; see rune-audit.log.' }
    Write-Output 'XUANCHI_REVIEW_BUILD_AND_AUDIT_SAVED'
    Set-ReviewStatus 'complete'
} catch {
    Set-ReviewStatus 'failed' $_.Exception.Message
    throw
} finally {
    if ($reviewHeld) { $reviewGate.ReleaseMutex() }
    $reviewGate.Dispose()
}
