param()
$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskOutput = Join-Path $taskProject 'SourceAssets/RSH12DualReloadDrop20261004'
$taskGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    # Wait for the currently running build; never interrupt it or queue a second
    # UBT process behind Build.bat's competing lock loop.
    do {
        $taskBuilders = @(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" |
            Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if ($taskBuilders.Count) {Start-Sleep -Seconds 15}
    } while ($taskBuilders.Count)
    while (-not $taskHeld) {
        try {$taskHeld = $taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld = $true}
    }
    $taskEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" |
        Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if ($taskEditors.Count) {throw 'FPSGAME editor or authoring commandlet is running; no process was stopped.'}
    $taskLog = Join-Path $taskProject 'Saved/BuildEditor/rsh12-dual-reload-drop-20261004.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development `
        '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -Module=FPSGAME `
        -MaxParallelActions=4 "-Log=$taskLog"
    if ($LASTEXITCODE -ne 0) {throw "RSH dual reload build failed ($LASTEXITCODE); see $taskLog"}
    $taskDll = Get-Item -LiteralPath (Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
    @{status='Succeeded'; log=$taskLog; dll=$taskDll.FullName; dllSavedAtUtc=$taskDll.LastWriteTimeUtc.ToString('o');
        runtimeTested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'build_receipt.json') -Encoding utf8
    Write-Output 'RSH_DUAL_RELOAD_DROP_BUILD_COMPLETE'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
