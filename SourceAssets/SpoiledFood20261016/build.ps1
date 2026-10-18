param([switch]$SkipEditor,[switch]$EditorOnly)
$ErrorActionPreference = 'Stop'
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
while (!$held) {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds(45)) }
    catch [Threading.AbandonedMutexException] { $held = $true }
    if (!$held) { Write-Output 'Waiting for the shared UE batch before the scoped build.' }
}
$projectRoot = 'D:/FPS3D/FPSGAME'
$taskRoot = Join-Path $projectRoot 'SourceAssets/SpoiledFood20261016'
$attempt = Get-Date -Format 'yyyyMMdd-HHmmss'
$attemptRoot = Join-Path $taskRoot $attempt
New-Item -ItemType Directory -Path $attemptRoot | Out-Null
Set-Location -LiteralPath $projectRoot
function Wait-BuildSlot {
    while ($true) {
        $active = @(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')
        })
        if (!$active.Count) { return }
        Write-Output "Waiting for current build $($active[0].ProcessId)."
        try { Wait-Process -Id $active[0].ProcessId -Timeout 45 -ErrorAction Stop }
        catch [System.TimeoutException] {}
        catch { if (Get-Process -Id $active[0].ProcessId -ErrorAction SilentlyContinue) { throw } }
    }
}
$targets = if ($EditorOnly) { @('FPSGAMEEditor') } elseif ($SkipEditor) { @('FPSGAME') } else { @('FPSGAMEEditor','FPSGAME') }
foreach ($target in $targets) {
    Wait-BuildSlot
    do {
    $projectProcesses = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq 'FPSGAME.exe' -or ($target -eq 'FPSGAMEEditor' -and $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and
        ([string]::IsNullOrEmpty($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject'))
    })
    if ($projectProcesses.Count) {
        if ($projectProcesses | Where-Object Name -ne 'UnrealEditor-Cmd.exe') {
            Write-Output 'An interactive editor/game is active; preserving it and stopping before build.'
            exit 75
        }
        Write-Output 'Waiting for the existing headless UE process to release the Editor module.'
        try { Wait-Process -Id $projectProcesses[0].ProcessId -Timeout 45 -ErrorAction Stop }
        catch [System.TimeoutException] {}
        catch { if (Get-Process -Id $projectProcesses[0].ProcessId -ErrorAction SilentlyContinue) { throw } }
    }
    } while ($projectProcesses.Count)
    Wait-BuildSlot
    Write-Output "Building $target; receipt $attemptRoot"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development `
        "-Project=$projectRoot/FPSGAME.uproject" '-NoHotReload' '-NoHotReloadFromIDE' '-MaxParallelActions=4' `
        "-Log=$attemptRoot/$target.log" *> "$attemptRoot/$target-console.log"
    if ($LASTEXITCODE -ne 0) { Write-Output "Build failed: $target"; exit $LASTEXITCODE }
}
@{attempt=$attempt;builds='Succeeded';targets=$targets;editor_skipped=$SkipEditor.IsPresent;game_run=$false} | ConvertTo-Json | Set-Content -Encoding UTF8 "$attemptRoot/result.json"
Write-Output "Spoiled food build receipt: $attemptRoot/result.json"
} finally { if ($held) { $gate.ReleaseMutex() }; $gate.Dispose() }
