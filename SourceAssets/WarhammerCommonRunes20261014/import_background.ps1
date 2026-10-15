$ErrorActionPreference = 'Stop'
$taskRoot = 'D:\FPS3D\FPSGAME\SourceAssets\WarhammerCommonRunes20261014'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
    if (-not $held) { throw 'Asset batch is busy; import not started.' }
    $existing = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' }
    if ($existing) { throw 'Project editor or commandlet is active; use the existing bridge.' }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=PythonScript "-script=$taskRoot\install_material.py" -unattended -nop4 -nosplash -nosound -NullRHI "-abslog=$taskRoot\import-engine.log" *> "$taskRoot\import-console.log"
    $code = $LASTEXITCODE
    @{exit_code=$code;game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot\commandlet_receipt.json" -Encoding UTF8
    exit $code
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
