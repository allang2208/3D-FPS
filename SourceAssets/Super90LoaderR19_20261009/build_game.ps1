param([int]$QueueWaitSeconds = 60)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous UE batch ended unexpectedly; no build started.' }
    if (-not $held) { throw 'UE batch gate is busy; no build started.' }
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('FPSGAME.exe','cl.exe','link.exe','UnrealBuildTool.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($busy.Count) { throw 'A game or native build is active; no build started.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $gameLog = "$PSScriptRoot/build-game-$stamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$gameLog" *> "$PSScriptRoot/build-game-console-$stamp.log"
    if ($LASTEXITCODE -ne 0) { throw "Game build failed; see $gameLog" }
    [ordered]@{ completed=$true; gameLog="build-game-$stamp.log"; editorBaseBuilt=$false; runtimeTested=$false } |
        ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/game_build_receipt.json" -Encoding utf8
    Write-Output 'R19 Game build saved; the running editor was not closed or rebuilt.'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
