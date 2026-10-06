param([switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskOutput = Join-Path $taskProject 'SourceAssets/RSH12UnifiedGrip20261004'
$taskLog = Join-Path $taskProject 'Saved/BuildEditor/rsh12-unified-grip-20261004.log'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    while (-not $taskHeld) {
        try { $taskHeld = $taskGate.WaitOne(15000) } catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    }
    while ($true) {
        $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
        })
        if ($taskEditors | Where-Object { $_.Name -eq 'UnrealEditor.exe' }) { throw 'FPSGAME editor is open; no editor was stopped.' }
        $taskBuilders = @(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {
            $_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'
        })
        if ($taskEditors.Count -eq 0 -and $taskBuilders.Count -eq 0) { break }
        Start-Sleep -Seconds 15
    }
    if (-not $BuildOnly) {
        & "$taskProject/Tools/ModularOutfit/Run-Authoring.ps1" -Script 'SourceAssets/RSH12UnifiedGrip20261004/import_profile.py' -Log 'SourceAssets/RSH12UnifiedGrip20261004/import_commandlet.log'
        if ($LASTEXITCODE -ne 0) { throw 'RSH grip asset import failed.' }
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -Module=FPSGAME -MaxParallelActions=4 "-Log=$taskLog"
    if ($LASTEXITCODE -ne 0) { throw "RSH grip build failed ($LASTEXITCODE)." }
    $taskDll = Get-Item -LiteralPath (Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
    @{ status='Succeeded'; target='FPSGAMEEditor Win64 Development -Module=FPSGAME'; log=$taskLog; dll=$taskDll.FullName; dllBytes=$taskDll.Length; dllSavedAtUtc=$taskDll.LastWriteTimeUtc.ToString('o'); runtimeTested=$false } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'build_receipt.json') -Encoding utf8
    Write-Output 'RSH12_UNIFIED_GRIP_PIPELINE_COMPLETE'
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
