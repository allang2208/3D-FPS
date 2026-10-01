$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'The UE authoring/build batch is busy.' }
    $running = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if ($running | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject' }) { throw 'FPSGAME is open; no editor was stopped.' }
    $compilers = @(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'")
    if ($compilers | Where-Object { $_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool' }) { throw 'An existing compiler is running; this build was not submitted.' }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -DisableUnity -NoUBA -Module=FPSGAME -MaxParallelActions=4 '-Log=D:/FPS3D/FPSGAME/Saved/BuildEditor/hk416-common-attachments-20260930.log'
    if ($LASTEXITCODE -ne 0) { throw "Editor build failed ($LASTEXITCODE)" }
    $receipt = @{ status = 'Editor DLL built and saved'; target = 'FPSGAMEEditor Win64 Development -Module=FPSGAME'; maxParallelActions = 4; log = 'Saved/BuildEditor/hk416-common-attachments-20260930.log'; runtimeTested = $false }
    $receipt | ConvertTo-Json | Set-Content -LiteralPath "$projectRoot/SourceAssets/HK416CommonAttachments20260930/build_receipt.json" -Encoding utf8
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
