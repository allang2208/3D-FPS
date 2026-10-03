$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskEditorCode=$null
$taskGameCode=$null
try {
    try {$taskHeld=$taskMutex.WaitOne(0)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if (-not $taskHeld) {Write-Output 'Waiting for the current UE batch.'}
    while (-not $taskHeld) {try {$taskHeld=$taskMutex.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    $taskEditors=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object {$_.CommandLine -like '*FPSGAME*' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-run='}
    if ($taskEditors) {throw 'Preserve the running FPSGAME editor/game; native background link cannot overwrite its loaded DLL.'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development "-project=$taskProject\FPSGAME.uproject" -NoHotReloadFromIDE *> (Join-Path $taskRoot 'Receipts/editor-build.log')
    $taskCode=$LASTEXITCODE
    Write-Output "STAFF_EDITOR_BUILD_EXIT=$taskCode"
    $taskEditorCode=$taskCode
    if ($taskCode -ne 0) {throw 'Editor build failed; see this task build log.'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAME Win64 Development "-project=$taskProject\FPSGAME.uproject" -NoHotReloadFromIDE *> (Join-Path $taskRoot 'Receipts/game-build.log')
    $taskCode=$LASTEXITCODE
    Write-Output "STAFF_GAME_BUILD_EXIT=$taskCode"
    $taskGameCode=$taskCode
    if ($taskCode -ne 0) {throw 'Game build failed; see this task build log.'}
    @{stage='binaries_saved';editor_exit=$taskEditorCode;game_exit=$taskGameCode;built_at=(Get-Date).ToString('s');tests_run=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'Receipts/native-build.json') -Encoding UTF8
} catch {
    @{stage='build_blocked';editor_exit=$taskEditorCode;game_exit=$taskGameCode;built_at=(Get-Date).ToString('s');editor_log='Receipts/editor-build.log';game_log='Receipts/game-build.log';reason=$_.Exception.Message;tests_run=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'Receipts/native-build.json') -Encoding UTF8
    throw
} finally {
    if ($taskHeld) {$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
