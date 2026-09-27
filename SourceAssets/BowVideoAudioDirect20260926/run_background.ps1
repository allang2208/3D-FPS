param([int]$WaitSeconds = 900)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$caseRoot = $PSScriptRoot
$logRoot = Join-Path $projectRoot 'Saved\BowVideoAudioDirect20260926'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$deadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
$announced = $false
while ($true) {
    $native = Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -match '^(cl|link)\.exe$') -or
        ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')
    }
    if (-not $native) { break }
    if (-not $announced) { Write-Output '[queue] Waiting for the running native build before audio import.'; $announced = $true }
    if ([DateTime]::UtcNow -ge $deadline) { throw 'Native build is still busy. No running process was stopped.' }
    Start-Sleep -Seconds 5
}
$existing = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
    Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME' }
if ($existing) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$projectRoot\Tools\AssetPipeline\mcp_call_codex.ps1" `
        -PythonScript "$caseRoot\import_audio.py" -QueueWaitSeconds 60 `
        -OutputFile "$logRoot\import-retry-response.json" -MaxOutputChars 3000
} else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$projectRoot\SourceAssets\DarkBow20260925\Scripts\run_headless.ps1" `
        -Script "$caseRoot\import_audio.py" -LogName 'bow-video-direct-import.log' -MutexWaitSeconds $WaitSeconds
}
if ($LASTEXITCODE -ne 0) { throw 'Direct-video audio import did not complete. Configuration has not been switched.' }
& py -3.11 "$caseRoot\install_config.py"
if ($LASTEXITCODE -ne 0) { throw 'Saved audio is available, but configuration activation did not complete.' }
Write-Output '[import] Both direct-video sounds saved and activated.'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$projectRoot\SourceAssets\BowAudioStillNorth20260926\run_background.ps1" `
    -BuildOnly -WaitSeconds $WaitSeconds -BuildLogName 'build-bow-hip-aim-original-audio-20260926.log'
exit $LASTEXITCODE
