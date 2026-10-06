param()
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $taskProject 'SourceAssets/RSH12HeavyGrip20261004/Integration20261005'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    while ($true) {
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
        if ($taskEditors | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {throw 'FPSGAME editor is open and occupies the base DLL; no editor was stopped.'}
        $taskBuilders=@(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if ($taskEditors.Count -eq 0 -and $taskBuilders.Count -eq 0) {break}
        Start-Sleep -Seconds 15
    }
    $taskLog=Join-Path $taskProject 'Saved/BuildEditor/rsh12-heavy-grip-20261005.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -Module=FPSGAME -MaxParallelActions=4 "-Log=$taskLog"
    if ($LASTEXITCODE -ne 0) {throw "RSH heavy grip build failed ($LASTEXITCODE)."}
    $taskDll=Get-Item -LiteralPath (Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
    @{status='Succeeded';log=$taskLog;dll=$taskDll.FullName;dllSavedAtUtc=$taskDll.LastWriteTimeUtc.ToString('o');runtimeTested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'build_receipt.json') -Encoding utf8
    Write-Output 'RSH_HEAVY_GRIP_BUILD_COMPLETE'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
