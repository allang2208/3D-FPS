param([int]$WaitSeconds = 900)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$deadline = [DateTime]::UtcNow.AddSeconds($WaitSeconds)
$announced = $false
while ($true) {
    $busy = Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match '^UnrealEditor.*\.exe$' -and
            (-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME')) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -match '^(cl|link)\.exe$') -or
        ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')
    }
    if (-not $busy) { break }
    if (-not $announced) {
        Write-Output ('[queue] Waiting for UE/build: ' + ($busy.ProcessId -join ', '))
        $announced = $true
    }
    if ([DateTime]::UtcNow -ge $deadline) { throw 'Workspace busy; no process was closed.' }
    Start-Sleep -Seconds 5
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
    "$projectRoot\SourceAssets\DarkBow20260925\Scripts\run_headless.ps1" `
    -Script "$PSScriptRoot\import_actions.py" -LogName 'bow-reference-v10-import.log' `
    -MutexWaitSeconds $WaitSeconds
exit $LASTEXITCODE
