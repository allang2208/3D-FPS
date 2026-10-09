$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    # Use the same authoring gate; never start a second native build.
    for ($attempt = 0; $attempt -lt 10 -and -not $held; ++$attempt) {
        try { $held = $gate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $held = $true }
        if ($held) {
            $activeBuilds = @(Get-CimInstance Win32_Process | Where-Object {
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
                $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe'
            })
            if ($activeBuilds.Count -gt 0) {
                $gate.ReleaseMutex(); $held = $false
                Write-Output 'An existing native build is active; waiting for its window.'
                Start-Sleep -Seconds 30
            }
        }
    }
    if (-not $held) { throw 'The existing UE batch is still busy; no build or import was started.' }
    $editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if ($editors | Where-Object { [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject' }) {
        throw 'FPSGAME editor is active. Preserve it and use the existing bridge for importing; native build must wait.'
    }
    Write-Output 'Building Editor modules for Super90 sprint and revised loader clocks.'
    & "$projectRoot/Tools/Build/Build-Editor.ps1"
    Write-Output 'Importing and saving revised loader animations and grip profiles in the background.'
    & "$projectRoot/Tools/ModularOutfit/Run-Authoring.ps1" `
        -Script 'SourceAssets/Super90MotionRevision20261007/import_motion.py' `
        -Log 'SourceAssets/Super90MotionRevision20261007/import_commandlet.log' `
        *> "$projectRoot/SourceAssets/Super90MotionRevision20261007/import_console.log"
    Write-Output 'Super90 Editor build and motion asset save completed; no runtime test was started.'
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
