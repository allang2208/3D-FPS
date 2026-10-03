param([int]$WaitSeconds=900)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$deadline=[DateTime]::UtcNow.AddSeconds($WaitSeconds)
$announced=$false
while ($true) {
    $processes=Get-CimInstance Win32_Process
    $commandlets=$processes | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -and (-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME') }
    $games=$processes | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME' -and $_.CommandLine -match '(?i)(?:^|\s)-game(?:\s|$)' }
    $builds=$processes | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -match '^(cl|link)\.exe$' }
    if (-not $commandlets -and -not $games -and -not $builds) { break }
    if (-not $announced) { Write-Output '[queue] Waiting for the current background UE/build operation to finish.'; $announced=$true }
    if ([DateTime]::UtcNow -ge $deadline) { throw 'Current background job is still running; source preserved.' }
    Start-Sleep -Seconds 5
}
$editors=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { (-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME') -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)' }
if ($editors) {
    $output=Join-Path $PSScriptRoot ('mcp-import-'+[DateTime]::Now.ToString('yyyyMMdd-HHmmss')+'.json')
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$projectRoot\Tools\AssetPipeline\mcp_call_codex.ps1" `
        -PythonScript "$PSScriptRoot\import_assets.py" -QueueWaitSeconds $WaitSeconds -OutputFile $output -MaxOutputChars 2000
} else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$projectRoot\SourceAssets\DarkBow20260925\Scripts\run_headless.ps1" `
        -Script "$PSScriptRoot\import_assets.py" -LogName 'bow-surface-repair-20260927-import.log' -MutexWaitSeconds $WaitSeconds `
        *> "$PSScriptRoot\import-console.log"
}
if ($LASTEXITCODE -ne 0) { throw 'Asset import did not finish; catalog not activated.' }
Write-Output '[done] Four bow surfaces saved in existing paths; no catalog switch required.'

