$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    while ($true) {
        while (-not $held) {
            try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
        }
        $running = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject'
        })
        if ($running | Where-Object { $_.Name -eq 'UnrealEditor.exe' }) { throw 'FPSGAME is open; no editor was stopped.' }
        $compilers = @(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {
            $_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'
        })
        if ($running.Count -eq 0 -and $compilers.Count -eq 0) { break }
        # Other projects can build without this project's batch gate. Release it
        # while waiting; do not submit a competing UBT build or hold up authoring.
        $gate.ReleaseMutex(); $held = $false
        Start-Sleep -Seconds 15
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -DisableUnity -NoUBA -Module=FPSGAME -MaxParallelActions=4 '-Log=D:/FPS3D/FPSGAME/Saved/BuildEditor/rifle-hip-standard-20260930.log'
    if ($LASTEXITCODE -ne 0) { throw "Editor build failed ($LASTEXITCODE)" }
    $receipt = @{ status = 'Editor DLL built and saved'; target = 'FPSGAMEEditor Win64 Development -Module=FPSGAME'; maxParallelActions = 4; log = 'Saved/BuildEditor/rifle-hip-standard-20260930.log'; runtimeTested = $false }
    $receipt | ConvertTo-Json | Set-Content -LiteralPath "$projectRoot/SourceAssets/RifleHipStandard20260930/build_receipt.json" -Encoding utf8
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
