param([int]$QueueWaitSeconds = 60)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
# UBT -WaitMutex queues behind the native compiler. The bridge gate protects
# the whole integration batch, while loaded editor/game binaries still block it.
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous UE batch ended unexpectedly; no build started.' }
    if (-not $held) { throw 'UE batch gate is busy; no build started.' }
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe')
    })
    if ($busy.Count) { throw 'An editor or game is active; no build started.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    & "$projectRoot/Tools/Build/Build-Editor.ps1" *> "$PSScriptRoot/build-editor-$stamp.log"
    $gameLog = "$PSScriptRoot/build-game-$stamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$gameLog" *> "$PSScriptRoot/build-game-console-$stamp.log"
    if ($LASTEXITCODE -ne 0) { throw "Game build failed; see $gameLog" }
    [ordered]@{ completed=$true; editorLog="build-editor-$stamp.log"; gameLog="build-game-$stamp.log"; runtimeTested=$false } |
        ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_receipt.json" -Encoding utf8
    Write-Output 'R17 restore Editor and Game builds saved; no editor or game launched.'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
