param([string]$Attempt='01')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if (-not $taskHeld) {throw 'Asset queue timed out.'}
    if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {throw 'A UE process is active; preserve it and use the existing bridge if needed.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/install_assets.py" '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/import-commandlet-$Attempt.log" *> "$taskRoot/import-console-$Attempt.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/commandlet-receipt-$Attempt.json" -Encoding UTF8
    if ($taskExit -ne 0) {throw "Zhanmadao import failed ($taskExit)."}
    Write-Output 'ZHANMADAO_ASSETS_SAVED'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
