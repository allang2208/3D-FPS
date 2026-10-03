# Wait for the authoring gate to go quiet, then import the reweighted PKM bare palm
# and bake it into the PKM viewmodel.
#
# Another conversation is running a series of FPSGAME commandlets, and Run-Authoring.ps1
# refuses to start while any FPSGAME editor/commandlet is alive.  Per the project rules
# we neither kill their process nor message that conversation, so this waits for a quiet
# window instead of busy-polling by hand.  The gate's own mutex still serialises the
# batch once we do start.
param(
    [int]$MaxMinutes = 60,
    [int]$QuietSeconds = 25
)
$ErrorActionPreference = 'Continue'
$project = 'D:\FPS3D\FPSGAME'
$runAuthoring = Join-Path $project 'Tools\ModularOutfit\Run-Authoring.ps1'
$logs = Join-Path $project 'SourceAssets\PKMLowpoly20260922\Sprint46\Logs'
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

$steps = @(
    @{ Name = 'import_bare_palm_v7'; Script = 'Tools/ModularOutfit/import_bare_palm_v7.py'; Log = 'SourceAssets/PKMLowpoly20260922/Sprint46/Logs/import_v7.log' },
    @{ Name = 'bake_native_bare_defaults_v7'; Script = 'Tools/ModularOutfit/bake_native_bare_defaults_v7.py'; Log = 'SourceAssets/PKMLowpoly20260922/Sprint46/Logs/bake_v7.log' }
)
foreach ($s in $steps) {
    Write-Output ("STEP_BEGIN " + $s.Name + " " + (Get-Date -Format 'HH:mm:ss'))
    try {
        & $runAuthoring -Script $s.Script -Log $s.Log
        Write-Output ("STEP_OK " + $s.Name + " exit=" + $LASTEXITCODE)
    }
    catch {
        Write-Output ("STEP_FAIL " + $s.Name + " : " + $_.Exception.Message)
        exit 3
    }
}
Write-Output 'SPRINT46_PIPELINE_DONE'