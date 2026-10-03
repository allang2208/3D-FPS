# Re-import the isotropised SkinMicro texture once the authoring gate is quiet.
#
# Multiple sessions are working in this repo at the same time, so this never starts while
# any FPSGAME editor/commandlet is alive - it waits for a quiet window and then lets
# Run-Authoring.ps1's own batch mutex serialise the actual import.  It never kills another
# session's process and never messages another session.
param(
    [int]$MaxMinutes = 60,
    [int]$QuietSeconds = 25
)
$ErrorActionPreference = 'Continue'
$project = 'D:\FPS3D\FPSGAME'
$runAuthoring = Join-Path $project 'Tools\ModularOutfit\Run-Authoring.ps1'
$logs = Join-Path $project 'SourceAssets\PKMLowpoly20260922\Sprint47\Logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Get-Blockers {
    @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" -ErrorAction SilentlyContinue |
        Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME\.uproject' })
}

$deadline = (Get-Date).AddMinutes($MaxMinutes)
$quietSince = $null
Write-Output ("WAIT_BEGIN " + (Get-Date -Format 'HH:mm:ss') + " max ${MaxMinutes}min quiet ${QuietSeconds}s")

while ((Get-Date) -lt $deadline) {
    $b = Get-Blockers
    if ($b.Count -eq 0) {
        if (-not $quietSince) { $quietSince = Get-Date }
        if (((Get-Date) - $quietSince).TotalSeconds -ge $QuietSeconds) {
            Write-Output ("GATE_CLEAR " + (Get-Date -Format 'HH:mm:ss'))
            break
        }
    }
    else {
        $quietSince = $null
        $ids = ($b | ForEach-Object { $_.ProcessId }) -join ','
        Write-Output ("WAITING " + (Get-Date -Format 'HH:mm:ss') + " blocker PIDs " + $ids)
    }
    Start-Sleep -Seconds 10
}
if ((Get-Date) -ge $deadline) { Write-Output 'GATE_TIMEOUT'; exit 2 }

Write-Output ("STEP_BEGIN import_skin_micro_grain " + (Get-Date -Format 'HH:mm:ss'))
try {
    & $runAuthoring -Script 'Tools/ModularOutfit/import_skin_micro_grain.py' `
        -Log 'SourceAssets/PKMLowpoly20260922/Sprint47/Logs/import_micro.log'
    Write-Output ("STEP_OK exit=" + $LASTEXITCODE)
}
catch {
    Write-Output ("STEP_FAIL : " + $_.Exception.Message)
    exit 3
}
Write-Output 'SPRINT47_IMPORT_DONE'