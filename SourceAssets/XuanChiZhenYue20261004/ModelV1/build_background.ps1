$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne([TimeSpan]::FromMinutes(40)) }
    catch [Threading.AbandonedMutexException] { $held=$true }
    if (-not $held) { throw 'Background build queue timed out.' }
    $deadline=(Get-Date).AddMinutes(30)
    while (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
        if ((Get-Date) -gt $deadline) { throw 'A UE process still holds build outputs; left it running.' }
        Start-Sleep -Seconds 10
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReloadFromIDE -NoLiveCoding -NoUBA -MaxParallelActions=3 "-Log=$taskRoot/build-editor-02.log" *> "$taskRoot/build-console-02.log"
    $code=$LASTEXITCODE
    @{exit_code=$code;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build_receipt.json" -Encoding UTF8
    if ($code -ne 0) { throw "UE build failed ($code). See build-console-02.log." }
    Write-Output 'XUANCHI_EDITOR_BUILD_SAVED'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
