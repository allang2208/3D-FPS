$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME/SourceAssets/ShotgunIconsFramed20261015'
$project = 'D:/FPS3D/FPSGAME/FPSGAME.uproject'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(600000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { Write-Output 'ASSET_WINDOW_STILL_BUSY'; exit 75 }
    $editor = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") | Where-Object { $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject' }
    if ($editor) {
        $gate.ReleaseMutex(); $held = $false
        & powershell -NoProfile -File 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript "$taskRoot/import_icons.py" -OutputFile "$taskRoot/install_bridge_01.json" -MaxOutputChars 1800 -QueueWaitSeconds 600 -RequestTimeoutSeconds 240
    } else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $project -run=pythonscript "-script=$taskRoot/import_icons.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$taskRoot/install_engine_rhi.log"
    }
    exit $LASTEXITCODE
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
