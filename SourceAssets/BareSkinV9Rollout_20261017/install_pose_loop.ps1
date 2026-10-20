param([string]$Batches = 'batch1,batch2,batch3,batch4', [string]$Sub = '_pose', [string]$Accept = 'Installed', [int]$MaxRuns = 16)
# JC_Pose_* example correctives (Work/<batch><Sub>): morph-only installs on meshes still exactly as this rollout last
# wrote them (receipt hash in one of the $Accept receipt dirs). Resumable per receipt (Installed<Sub>/).
$ErrorActionPreference = 'Stop'
$env:V9R_BATCHES = $Batches; $env:V9R_SUBDIR = $Sub; $env:V9R_ACCEPT_DIRS = $Accept
function Remaining {
    $n = 0
    foreach ($b in $Batches.Split(',')) {
        $d = Join-Path $PSScriptRoot "Work\$b$Sub"
        if (-not (Test-Path $d)) { continue }
        Get-ChildItem $d -Filter '*.json' | Where-Object { $_.BaseName -match '^[0-9a-f]{12}$' } | ForEach-Object {
            if (-not (Test-Path (Join-Path $PSScriptRoot "Installed$Sub\$($_.BaseName).json"))) { $n++ }
        }
    }
    $n
}
for ($i = 0; $i -lt $MaxRuns; $i++) {
    $left = Remaining
    Write-Output "run $i : $left meshes left"
    if ($left -eq 0 -and $i -gt 0) { break }
    try { & (Join-Path $PSScriptRoot 'wait_and_run.ps1') -ScriptName run_installs.py } catch { Write-Output "run failed: $($_.Exception.Message)" }
}
Write-Output "V9R_POSE_LOOP_DONE left=$(Remaining)"
