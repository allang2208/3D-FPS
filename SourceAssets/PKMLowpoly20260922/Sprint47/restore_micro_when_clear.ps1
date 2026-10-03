# Complete the SkinMicro rollback import in a quiet window (merge point, 2026-09-26).
#
# Same philosophy as run_import_when_clear.ps1, with three corrections:
#   1) writes a NEW log Logs\restore_micro.log - never overwrites the 23:13 evidence
#      log import_micro.log (rollback audit trail);
#   2) also treats active UBT builds (UnrealBuildTool dotnet / cl.exe / link.exe) as
#      blockers, so the commandlet never holds UnrealEditor-FPSGAME.dll during another
#      session's link phase (WORKFLOW.md §7 build-serialisation rules, 2026-09-26);
#   3) retries the batch gate a bounded number of times instead of failing once.
#
# Never kills another session's process, never messages another session.
param(
    [int]$MaxMinutes = 90,
    [int]$QuietSeconds = 25,
    [int]$MaxAttempts = 3
)
$ErrorActionPreference = 'Continue'
$project = 'D:\FPS3D\FPSGAME'
$runAuthoring = Join-Path $project 'Tools\ModularOutfit\Run-Authoring.ps1'
$logs = Join-Path $project 'SourceAssets\PKMLowpoly20260922\Sprint47\Logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

function Get-Blockers {
    $editor = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" -ErrorAction SilentlyContinue |
        Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME\.uproject' })
    $ubt = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'UnrealBuildTool' })
    $compilers = @(Get-Process -Name 'cl', 'link' -ErrorAction SilentlyContinue)
    return @($editor) + @($ubt) + @($compilers)
}

$deadline = (Get-Date).AddMinutes($MaxMinutes)
$attempt = 0
Write-Output ("WAIT_BEGIN " + (Get-Date -Format 'HH:mm:ss') + " max ${MaxMinutes}min quiet ${QuietSeconds}s attempts ${MaxAttempts}")

while ((Get-Date) -lt $deadline -and $attempt -lt $MaxAttempts) {
    # --- wait for a quiet window ---
    $quietSince = $null
    $clear = $false
    while ((Get-Date) -lt $deadline) {
        $b = @(Get-Blockers)
        if ($b.Count -eq 0) {
            if (-not $quietSince) { $quietSince = Get-Date }
            if (((Get-Date) - $quietSince).TotalSeconds -ge $QuietSeconds) {
                Write-Output ("GATE_CLEAR " + (Get-Date -Format 'HH:mm:ss'))
                $clear = $true
                break
            }
        }
        else {
            $quietSince = $null
            $desc = ($b | ForEach-Object { if ($_.ProcessId) { $_.ProcessId } else { $_.Id } }) -join ','
            Write-Output ("WAITING " + (Get-Date -Format 'HH:mm:ss') + " blockers " + $desc)
        }
        Start-Sleep -Seconds 10
    }
    if (-not $clear) { break }

    # --- run the import through Run-Authoring's own batch mutex ---
    $attempt++
    Write-Output ("STEP_BEGIN restore_skin_micro attempt=" + $attempt + " " + (Get-Date -Format 'HH:mm:ss'))
    try {
        & $runAuthoring -Script 'Tools/ModularOutfit/import_skin_micro_grain.py' `
            -Log 'SourceAssets/PKMLowpoly20260922/Sprint47/Logs/restore_micro.log'
        Write-Output ("STEP_OK exit=" + $LASTEXITCODE + " " + (Get-Date -Format 'HH:mm:ss'))
        Write-Output 'RESTORE_MICRO_DONE'
        exit 0
    }
    catch {
        Write-Output ("STEP_FAIL attempt=" + $attempt + " : " + $_.Exception.Message)
        Start-Sleep -Seconds 30
    }
}

if ($attempt -ge $MaxAttempts) { Write-Output 'RESTORE_MICRO_ATTEMPTS_EXHAUSTED'; exit 3 }
Write-Output 'GATE_TIMEOUT'; exit 2
