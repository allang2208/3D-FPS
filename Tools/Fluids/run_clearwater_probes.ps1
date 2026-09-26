# Drive the Clearwater surface probes: author -> capture -> file away, for each quantity.
#
# One probe = one pythonscript commandlet run (env CLEARWATER_PROBE selects it, see
# clearwater_probe_surface.py) + one -game capture through run_clearwater_capture.ps1, which
# is the only channel proven to produce a real frame in this environment. The final pass
# repoints MI_ClearwaterWater back at the real master; pass -NoRestore to keep the last probe
# active for manual inspection in the editor.
#
#     powershell -ExecutionPolicy Bypass -File Tools/Fluids/run_clearwater_probes.ps1
#     powershell -File Tools/Fluids/run_clearwater_probes.ps1 -Probes H,SCN
#
# Output: Saved/ClearwaterProbes/<name>.png, one per probe.
[CmdletBinding()]
param(
    [string[]]$Probes = @('H', 'NRM', 'SCN', 'CAUS', 'SKY'),
    [int]$Warmup = 12,
    [switch]$NoRestore
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Project = Join-Path $ProjectRoot "FPSGAME.uproject"
$Cmd = "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
$ProbeScript = Join-Path $PSScriptRoot "clearwater_probe_surface.py"
$OutDir = Join-Path $ProjectRoot "Saved/ClearwaterProbes"
$ShotDir = Join-Path $ProjectRoot "Saved/Screenshots/WindowsEditor"

foreach ($p in @($Cmd, $Project, $ProbeScript, (Join-Path $PSScriptRoot "run_clearwater_capture.ps1"))) {
    if (-not (Test-Path $p)) { throw "missing: $p" }
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Invoke-ProbeCommandlet([string]$Mode, [string]$LogName) {
    $env:CLEARWATER_PROBE = $Mode
    $log = Join-Path $ProjectRoot "Saved/Logs/$LogName"
    & $Cmd $Project "-run=pythonscript" "-script=$ProbeScript" -unattended -noP4 -nosplash -NullRHI "-abslog=$log" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "commandlet for mode '$Mode' exited $LASTEXITCODE; see $log"
    }
    if (-not (Select-String -Path $log -Pattern 'CLEARWATER PROBE OK' -Quiet)) {
        throw "commandlet for mode '$Mode' produced no OK marker; see $log"
    }
}

$results = @()
try {
    foreach ($probe in $Probes) {
        Write-Host "=== probe $probe : authoring ===" -ForegroundColor Cyan
        Invoke-ProbeCommandlet "activate:$probe" "cwprobe_${probe}_author.log"

        Write-Host "=== probe $probe : capturing ===" -ForegroundColor Cyan
        & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run_clearwater_capture.ps1") `
            -Warmup $Warmup -Tag "cwprobe_$probe"
        if ($LASTEXITCODE -ne 0) {
            throw "capture for probe $probe exited $LASTEXITCODE"
        }
        # The capture script just wrote the newest file in $ShotDir.
        $shot = Get-ChildItem $ShotDir -Filter 'ScreenShot*.png' -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $shot) { throw "no screenshot found for probe $probe" }
        $dest = Join-Path $OutDir "$probe.png"
        Copy-Item $shot.FullName $dest -Force
        $results += "  $probe -> $dest"
        Write-Host "filed: $dest"
    }
}
finally {
    if (-not $NoRestore) {
        Write-Host "=== restoring MI_ClearwaterWater ===" -ForegroundColor Cyan
        Invoke-ProbeCommandlet "restore" "cwprobe_restore.log"
    }
}

Write-Host ""
Write-Host "probe results:"
$results | ForEach-Object { Write-Host $_ }
