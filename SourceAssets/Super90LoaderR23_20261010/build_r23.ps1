param([int]$QueueWaitSeconds = 60)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$buildBatch = 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds)) }
    catch [Threading.AbandonedMutexException] { $held = $true; throw 'Previous UE batch ended unexpectedly; no build started.' }
    if (-not $held) { throw 'UE batch gate is busy; no build started.' }
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe','cl.exe','link.exe','UnrealBuildTool.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($busy.Count) { throw 'An editor, game or native build is active; no build started.' }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    foreach ($target in @('FPSGAMEEditor', 'FPSGAME')) {
        $log = "$PSScriptRoot/build-$target-$stamp.log"
        & $buildBatch $target Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$log" *> "$PSScriptRoot/build-$target-console-$stamp.log"
        if ($LASTEXITCODE -ne 0) { throw "$target build failed; see $log" }
    }
    [ordered]@{
        completed=$true
        editorLog="build-FPSGAMEEditor-$stamp.log"
        gameLog="build-FPSGAME-$stamp.log"
        runtimeTested=$false
    } | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_receipt.json" -Encoding utf8
    Write-Output 'R23 Editor and Game builds saved; no editor or game launched.'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
