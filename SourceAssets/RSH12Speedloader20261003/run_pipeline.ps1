param([switch]$BuildOnly)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(15000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    Write-Output 'RSH12 pipeline owns the shared asset/build window; waiting for already-running processes.'
    # Keep this one queued batch serialized from import through build. Releasing
    # between these dependent stages let later commandlets repeatedly take the gap.
    while ($true) {
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
        if ($taskEditors | Where-Object {$_.Name -eq 'UnrealEditor.exe'}) {throw 'FPSGAME editor reopened; no process was stopped.'}
        $taskBuilders=@(Get-CimInstance Win32_Process -Filter "Name='cl.exe' OR Name='dotnet.exe'" | Where-Object {$_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool'})
        if ($taskEditors.Count -eq 0 -and $taskBuilders.Count -eq 0) {break}
        Start-Sleep -Seconds 15
    }
    if (-not $BuildOnly) {
        Write-Output 'RSH12 importing the five-round loader assets.'
        & "$taskRoot/Tools/ModularOutfit/Run-Authoring.ps1" -Script 'SourceAssets/RSH12Speedloader20261003/import_assets.py' -Log 'SourceAssets/RSH12Speedloader20261003/import_commandlet.log'
        if ($LASTEXITCODE -ne 0) {throw 'RSH12 import failed; build was not started.'}
    }
    Write-Output 'RSH12 assets saved; building the base Editor DLL.'
    & "$taskRoot/SourceAssets/RSH12Speedloader20261003/build_editor.ps1"
    if ($LASTEXITCODE -ne 0) {throw 'RSH12 base build failed.'}
    Write-Output 'RSH12_PIPELINE_COMPLETE'
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
