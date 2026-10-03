# Frame-time capture for a staged packaged build (the cooked, no-editor runtime).
#
# Why it differs from run_standalone_capture.ps1 / run_daynight_capture.ps1, which run
# the editor or the uncooked game target:
#   1. it launches the staged package, so it never needs the project to be writable
#      and never needs the editor;
#   2. it does NOT pass -RenderOffscreen -- under that flag -ResX/-ResY do not take
#      effect (previously recorded: the capture stayed at 1280x720 no matter what);
#   3. it reads the log and GameUserSettings.ini back to report the ACTUAL render
#      resolution instead of trusting the requested one.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File Tools/Performance/run_packaged_capture.ps1 `
#     -PackageDir Saved/StagedBuilds/core-measurement-<ts> -Map DayNight_Lighting `
#     -ResX 2560 -ResY 1440 -Frames 1800 -Profile PkgCore1440
#
# Analysis afterwards:
#   python Tools/Performance/frame_budget.py --csv Saved/<Profile>/baseline.csv --gate 240

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PackageDir,
    [string]$Map = 'DayNight_Lighting',
    [int]$ResX = 2560,
    [int]$ResY = 1440,
    [int]$Frames = 1800,
    [string]$Profile = '',
    [switch]$Fullscreen,
    [string]$ExtraArgs = '',
    [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not [IO.Path]::IsPathRooted($PackageDir)) { $PackageDir = Join-Path $projectRoot $PackageDir }
$PackageDir = (Resolve-Path $PackageDir).Path

$exe = Join-Path $PackageDir 'Windows/FPSGAME.exe'
if (-not (Test-Path $exe)) {
    $exe = (Get-ChildItem $PackageDir -Recurse -Filter 'FPSGAME.exe' -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName)
}
if (-not $exe) { throw "packaged FPSGAME.exe not found under $PackageDir" }

if ([string]::IsNullOrWhiteSpace($Profile)) { $Profile = 'PkgCapture-' + (Get-Date -Format 'yyyyMMdd-HHmmss') }
$outDir = Join-Path $projectRoot "Saved/$Profile"
$logDir = Join-Path $projectRoot 'Saved/Logs'
New-Item -ItemType Directory -Force -Path $outDir, $logDir | Out-Null
$log = Join-Path $logDir "$Profile.log"

# A staged build writes its CsvProfiler output into its own Saved tree; an installed
# build may fall back to the engine-level directory, so check all plausible places.
$csvSearchDirs = @(
    (Join-Path $projectRoot 'Saved/Profiling/CSV'),
    (Join-Path (Split-Path $exe -Parent) '../../FPSGAME/Saved/Profiling/CSV'),
    (Join-Path $env:LOCALAPPDATA 'UnrealEngine/5.8/Saved/Profiling/CSV')
)

$mode = if ($Fullscreen) { '-fullscreen' } else { '-windowed' }
$arguments = @(
    "/Game/GameMaps/$Map"
    $mode
    "-ResX=$ResX"
    "-ResY=$ResY"
    '-unattended'
    '-nosplash'
    '-nosound'
    "-ColdSteelProfile=$Profile"
    "-csvCaptureFrames=$Frames"
    '-csvGpuStats'
    '-ExitAfterCsvProfiling'
    "-abslog=`"$log`""
)
if ($ExtraArgs -ne '') { $arguments += $ExtraArgs.Split('|') }

Write-Output "exe     : $exe"
Write-Output "map     : $Map  ($mode, $ResX x $ResY, $Frames frames)"
Write-Output "profile : $Profile"
Write-Output "log     : $log"

$started = Get-Date
$proc = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru
Write-Output "started pid $($proc.Id)"
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    Write-Warning "still running after $TimeoutSeconds s; killing pid $($proc.Id)"
    $proc.Kill()
    exit 2
}
Write-Output "exit code: $($proc.ExitCode)"

# --- verify the actual render resolution instead of trusting the request ---
$gameUserSettings = Get-ChildItem $PackageDir -Recurse -Filter 'GameUserSettings.ini' -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
if ($gameUserSettings) {
    Write-Output "--- GameUserSettings.ini ($gameUserSettings) ---"
    Select-String -Path $gameUserSettings -Pattern 'ResolutionSizeX|ResolutionSizeY|FullscreenMode|LastConfirmedFullscreenMode|bUseVSync|FrameRateLimit' |
        ForEach-Object { $_.Line.Trim() }
}
$resolutionEvidence = @()
if (Test-Path $log) {
    $resolutionEvidence = @(Select-String -Path $log -Pattern 'systemresolution\.(resx|resy)|ResolutionSize|r\.SetRes' -ErrorAction SilentlyContinue |
        Select-Object -First 12 | ForEach-Object { $_.Line.Trim() })
}
if ($resolutionEvidence.Count -gt 0) {
    Write-Output '--- log resolution evidence ---'
    $resolutionEvidence | ForEach-Object { Write-Output $_ }
} else {
    Write-Warning 'no resolution evidence in the log; treat the requested resolution as UNVERIFIED'
}

# --- collect the capture ---
$csv = $null
foreach ($dir in $csvSearchDirs) {
    if (-not (Test-Path $dir)) { continue }
    $candidate = Get-ChildItem $dir -Filter 'Profile(*).csv' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $started } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($candidate) { $csv = $candidate; break }
}
if (-not $csv) {
    Write-Warning "no CSV newer than $started in: $($csvSearchDirs -join ', ')"
    exit 3
}
$target = Join-Path $outDir 'baseline.csv'
Copy-Item $csv.FullName $target -Force
Write-Output "capture : $($csv.FullName)"
Write-Output "copied  : $target"

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    Write-Output '--- frame_budget.py (first 240 frames skipped) ---'
    & $python.Source (Join-Path $PSScriptRoot 'frame_budget.py') --csv $target --gate 240
}