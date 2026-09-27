param([int]$WaitSeconds = 1800)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$logs = Join-Path $projectRoot 'Saved\BowQuickCombatPush20260927'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Wait-ForWorkspace {
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
        if (-not $busy) { return }
        if (-not $announced) {
            Write-Output ('[queue] Waiting for UE/build processes: ' + ($busy.ProcessId -join ', '))
            $announced = $true
        }
        if ([DateTime]::UtcNow -ge $deadline) {
            throw 'Workspace remains busy. Authored files preserved; no process closed.'
        }
        Start-Sleep -Seconds 5
    }
}

Wait-ForWorkspace
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
    "$projectRoot\SourceAssets\DarkBow20260925\Scripts\run_headless.ps1" `
    -Script "$PSScriptRoot\import_push.py" -LogName 'bow-horizontal-push-20260927-import.log' `
    -MutexWaitSeconds $WaitSeconds *> "$logs\import-console.log"
if ($LASTEXITCODE -ne 0) { throw "Bow action import failed; see $logs\import-console.log" }
Write-Output '[import] Bow quick-combat animation saved.'

Wait-ForWorkspace
$modulePath = Join-Path $projectRoot 'Binaries\Win64\UnrealEditor-FPSGAME.dll'
$module = [IO.File]::Open($modulePath, 'Open', 'Read', 'None')
$module.Dispose()
Write-Output '[build] Building FPSGAMEEditor in background.'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' `
    FPSGAMEEditor Win64 Development "$projectRoot\FPSGAME.uproject" `
    *> "$logs\build-editor.log"
if ($LASTEXITCODE -ne 0) { throw "Editor build failed; see $logs\build-editor.log" }
Write-Output '[build] FPSGAMEEditor succeeded. No gameplay test or preview was run.'
