# Merge-point build for the F2 fix (PKMHandShading20260926, WORKFLOW.md §7 rule 3).
#
# Waits for a genuinely quiet window before submitting ONE consolidated build:
#   - no FPSGAME editor / commandlet alive (DLL not locked; Build-Editor.ps1 re-checks too),
#   - no UBT dotnet / cl.exe / link.exe alive (no other session's build in flight),
#   - Source/ untouched for StableSeconds (no parallel session mid-edit, §7.2).
# Never kills a process, never messages another session. On a raced failure it
# re-waits and retries once.
param(
    [int]$MaxMinutes = 240,
    [int]$QuietSeconds = 30,
    [int]$StableSeconds = 120,
    [int]$MaxAttempts = 2
)
$ErrorActionPreference = 'Continue'
$project = 'D:\FPS3D\FPSGAME'

function Get-Blockers {
    $editor = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" -ErrorAction SilentlyContinue |
        Where-Object { -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME\.uproject' })
    $ubt = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'UnrealBuildTool' })
    $compilers = @(Get-Process -Name 'cl', 'link' -ErrorAction SilentlyContinue)
    return @($editor) + @($ubt) + @($compilers)
}
function Test-SourceStable {
    $newest = (Get-ChildItem (Join-Path $project 'Source') -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.h', '.cpp', '.cs' } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    return $newest -and (((Get-Date) - $newest).TotalSeconds -ge $StableSeconds)
}
function Wait-QuietWindow {
    $deadline = (Get-Date).AddMinutes($MaxMinutes)
    $quietSince = $null
    while ((Get-Date) -lt $deadline) {
        $b = @(Get-Blockers)
        $stable = Test-SourceStable
        if ($b.Count -eq 0 -and $stable) {
            if (-not $quietSince) { $quietSince = Get-Date }
            if (((Get-Date) - $quietSince).TotalSeconds -ge $QuietSeconds) {
                Write-Output ("WINDOW_CLEAR " + (Get-Date -Format 'HH:mm:ss'))
                return $true
            }
        }
        else {
            $quietSince = $null
            $ids = ($b | ForEach-Object { if ($_.ProcessId) { $_.ProcessId } else { $_.Id } }) -join ','
            Write-Output ("WAITING " + (Get-Date -Format 'HH:mm:ss') + " blockers[" + $ids + "] sourceStable=" + $stable)
        }
        Start-Sleep -Seconds 20
    }
    Write-Output 'WINDOW_TIMEOUT'
    return $false
}

Write-Output ("WAIT_BEGIN " + (Get-Date -Format 'HH:mm:ss') + " max ${MaxMinutes}min quiet ${QuietSeconds}s source-stable ${StableSeconds}s")
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    if (-not (Wait-QuietWindow)) { exit 2 }
    Write-Output ("BUILD_BEGIN attempt=" + $attempt + " " + (Get-Date -Format 'HH:mm:ss'))
    try {
        & (Join-Path $project 'Tools\Build\Build-Editor.ps1')
        Write-Output ("BUILD_OK " + (Get-Date -Format 'HH:mm:ss'))
        Write-Output 'F2_BUILD_DONE'
        exit 0
    }
    catch {
        Write-Output ("BUILD_FAIL attempt=" + $attempt + " : " + $_.Exception.Message)
        Start-Sleep -Seconds 30
    }
}
Write-Output 'F2_BUILD_ATTEMPTS_EXHAUSTED'
exit 3
