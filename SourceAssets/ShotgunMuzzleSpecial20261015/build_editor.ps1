$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME/SourceAssets/ShotgunMuzzleSpecial20261015'
$deadline = [DateTime]::UtcNow.AddMinutes(12)
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    while ([DateTime]::UtcNow -lt $deadline) {
        $building = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='UnrealBuildTool.exe'") | Where-Object { $_.CommandLine -match 'UnrealBuildTool' }
        if ($building) {
            $observedBuild = Get-Process -Id $building[0].ProcessId -ErrorAction SilentlyContinue
            if ($observedBuild) { [void]$observedBuild.WaitForExit(10000) }
            continue
        }
        try { $held = $gate.WaitOne(1000) } catch [Threading.AbandonedMutexException] { $held = $true }
        if (-not $held) { continue }
        $running = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'") | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject' }
        if (-not $running) { break }
        $gate.ReleaseMutex(); $held = $false
        if ($running | Where-Object Name -eq 'UnrealEditor.exe') { Write-Output 'EDITOR_ACTIVE_USE_EXISTING_EDITOR_COMPILE'; exit 2 }
        Start-Sleep -Seconds 5
    }
    if (-not $held) { Write-Output 'BUILD_WINDOW_STILL_BUSY'; exit 75 }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskRoot/build_editor.log"
    $resultCode = $LASTEXITCODE
    @{ target='FPSGAMEEditor Win64 Development'; exitCode=$resultCode; runtimeTested=$false } | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build_editor_receipt.json" -Encoding utf8
    exit $resultCode
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
