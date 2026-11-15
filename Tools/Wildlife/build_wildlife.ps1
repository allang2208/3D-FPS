param([string]$ReceiptName = 'build-01')
$ErrorActionPreference = 'Stop'
$wlProject = 'D:/FPS3D/FPSGAME'
$wlRoot = Join-Path $wlProject 'SourceAssets/Wildlife20261022'
New-Item -ItemType Directory -Force -Path $wlRoot | Out-Null
$wlGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$wlHeld = $false
try {
    Write-Output 'Queued for the shared build window; existing builds finish first.'
    try { $wlHeld = $wlGate.WaitOne() } catch [Threading.AbandonedMutexException] { $wlHeld = $true }
    while ($true) {
        $wlBusy = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor.exe', 'UnrealEditor-Cmd.exe', 'UnrealBuildTool.exe', 'cl.exe', 'link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        if (-not $wlBusy.Count) { break }
        if (@($wlBusy | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(\s-game\b|\s-run=)' }).Count) {
            Write-Output 'An interactive editor holds the build; close it or build from there.'
            exit 75
        }
        try { Wait-Process -Id $wlBusy[0].ProcessId -Timeout 45 -ErrorAction Stop } catch [System.TimeoutException] {} catch { if (Get-Process -Id $wlBusy[0].ProcessId -ErrorAction SilentlyContinue) { throw } }
    }
    foreach ($wlTarget in @('FPSGAMEEditor', 'FPSGAME')) {
        $wlLog = Join-Path $wlRoot ($ReceiptName + '-' + $wlTarget + '.log')
        $wlOut = Join-Path $wlRoot ($ReceiptName + '-' + $wlTarget + '.txt')
        & dotnet 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll' $wlTarget Win64 Development "-Project=$wlProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$wlLog" *> $wlOut
        $wlExit = $LASTEXITCODE
        Get-Content -LiteralPath $wlOut -Tail 8
        if ($wlExit -ne 0) { exit $wlExit }
    }
    Write-Output 'WILDLIFE_BUILD_OK'
}
finally {
    if ($wlHeld) { $wlGate.ReleaseMutex() }
    $wlGate.Dispose()
}
