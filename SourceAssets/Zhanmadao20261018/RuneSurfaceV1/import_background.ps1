param([string]$Attempt='01')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if (-not $taskHeld) {throw 'Asset queue timed out.'}
    $taskDeadline=(Get-Date).AddMinutes(30)
    while ($true) {
        $taskEditors=Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue
        $taskUbt=Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" | Where-Object { $_.CommandLine -like '*UnrealBuildTool.dll*' }
        if (-not $taskEditors -and -not $taskUbt) {break}
        if ((Get-Date) -gt $taskDeadline) {throw 'Existing UE/build process remains active; preserved it and the prepared assets.'}
        Start-Sleep -Seconds 5
    }
    if (Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {throw 'A UE process started before import; preserve it and resubmit after it finishes.'}
    if (Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" | Where-Object { $_.CommandLine -like '*UnrealBuildTool.dll*' }) {throw 'A native build started before import; preserve it and resubmit after it finishes.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/install_assets.py" '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/import-commandlet-$Attempt.log" *> "$taskRoot/import-console-$Attempt.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/commandlet-receipt-$Attempt.json" -Encoding UTF8
    if ($taskExit -ne 0) {throw "Zhanmadao rune materials import failed ($taskExit)."}
    Write-Output 'ZHANMADAO_NATIVE_RUNES_SAVED'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()
}
