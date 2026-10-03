$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskOutputRoot = $PSScriptRoot
$taskLog = Join-Path $taskProjectRoot 'Saved/BuildEditor/pit-viper2011-optic-preview-fix-20261002.log'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    while ($true) {
        while (-not $taskHeld) {
            try { $taskHeld = $taskGate.WaitOne(15000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
        }
        $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject'
        })
        if ($taskEditors | Where-Object { $_.Name -eq 'UnrealEditor.exe' }) {
            if (-not $taskWaitingReported) { Write-Output 'Waiting for FPSGAME editor exit; no editor was closed.'; $taskWaitingReported = $true }
            $taskGate.ReleaseMutex(); $taskHeld = $false; Start-Sleep -Seconds 15; continue
        }
        $taskCompilers = @(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='link.exe' OR Name='dotnet.exe'" | Where-Object {
            $_.Name -ne 'dotnet.exe' -or $_.CommandLine -match 'UnrealBuildTool'
        })
        if ($taskEditors.Count -eq 0 -and $taskCompilers.Count -eq 0) { break }
        $taskGate.ReleaseMutex(); $taskHeld = $false
        Start-Sleep -Seconds 15
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -Module=FPSGAME -MaxParallelActions=4 "-Log=$taskLog"
    if ($LASTEXITCODE -ne 0) { throw "Editor build failed ($LASTEXITCODE). Log: $taskLog" }
    $taskDll = Get-Item -LiteralPath (Join-Path $taskProjectRoot 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
    @{ status='Succeeded'; target='FPSGAMEEditor Win64 Development -Module=FPSGAME'; log=$taskLog; dll=$taskDll.FullName; dllBytes=$taskDll.Length; dllSavedAtUtc=$taskDll.LastWriteTimeUtc.ToString('o'); runtimeTested=$false } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutputRoot 'build_receipt.json') -Encoding utf8
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
