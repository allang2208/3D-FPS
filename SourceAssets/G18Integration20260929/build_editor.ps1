$ErrorActionPreference = 'Stop'
$g18Project = 'D:/FPS3D/FPSGAME'
$g18Gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$g18Held = $false
try {
    try { $g18Held = $g18Gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $g18Held = $true }
    if (-not $g18Held) { throw 'The UE asset batch is busy; no build was started.' }
    $g18Running = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
    })
    if ($g18Running.Count -gt 0) { throw 'An editor is running; existing processes were preserved.' }
    $g18Building = @(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'cl.exe'
    })
    if ($g18Building.Count -gt 0) { throw 'An existing native build must finish before this build is submitted.' }
    # Submit only while idle; -WaitMutex covers a race after the process snapshot.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$g18Project/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE "-Log=$g18Project/SourceAssets/G18Integration20260929/build_ubt.log"
    if ($LASTEXITCODE -ne 0) { throw "G18 editor build failed: $LASTEXITCODE" }
    Write-Output 'G18_BUILD_COMPLETE; runtime testing remains manual.'
} finally {
    if ($g18Held) { $g18Gate.ReleaseMutex() }
    $g18Gate.Dispose()
}
