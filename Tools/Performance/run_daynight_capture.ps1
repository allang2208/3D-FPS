# CsvProfiler capture for FPSGAME hitch work (2026-09-21).
#
# Runs the project as an offscreen standalone game inside the editor process with
# CsvProfiler active, waits for it to exit on its own, then copies the capture to
# a stable path. It never opens PIE and never touches an interactive editor
# session, so it is safe to run while the editor is open.
#
# Engine behaviour: the CSV lands in Saved/Profiling/CSV/Profile(<timestamp>).csv
# (FCsvProfiler::GetDefaultDirectory) and -ExitAfterCsvProfiling ends the process.
# This script renames it to Saved/<Profile>/baseline.csv.
#
# Usage:
#   pwsh -File Tools/Performance/run_daynight_capture.ps1
#   pwsh -File Tools/Performance/run_daynight_capture.ps1 -Profile HitchProbe2 -Frames 1800
#
# Analysis afterwards:
#   python Tools/Performance/analyze_daynight_csv.py Saved/<Profile>/baseline.csv
#   python Tools/Performance/attribute_hitches.py Saved/<Profile>/baseline.csv
#   python Tools/Performance/dump_hitch_frames.py Saved/<Profile>/baseline.csv --threshold 25
[CmdletBinding()]
param(
    [string]$Profile = "DayNightPerfB20260921",
    [string]$Map = "DayNight_Lighting",
    [int]$Frames = 1200,
    [int]$ResX = 1280,
    [int]$ResY = 720,
    [string]$ExtraArgs = "",
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Project = Join-Path $ProjectRoot "FPSGAME.uproject"
$Editor = "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
$OutDir = Join-Path $ProjectRoot "Saved/$Profile"
$Log = Join-Path $ProjectRoot "Saved/Logs/$Profile.log"
$CsvDir = Join-Path $ProjectRoot "Saved/Profiling/CSV"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if (-not (Test-Path $Editor)) { throw "editor not found: $Editor" }
if (-not (Test-Path $Project)) { throw "project not found: $Project" }

$started = Get-Date
$arguments = @(
    "`"$Project`""
    "/Game/GameMaps/$Map"
    "-game"
    "-RenderOffscreen"
    "-unattended"
    "-nosplash"
    "-nosound"
    "-ResX=$ResX"
    "-ResY=$ResY"
    "-ColdSteelProfile=$Profile"
    "-csvCaptureFrames=$Frames"
    "-csvGpuStats"
    "-ExitAfterCsvProfiling"
    "-abslog=`"$Log`""
)
# -ExecCmds is comma separated and each command is trimmed, so a command that
# takes a value must use '=' (or quotes) rather than a space separator.
if ($ExtraArgs -ne "") { $arguments += $ExtraArgs.Split("|") }

Write-Host "profile : $Profile"
Write-Host "map     : $Map ($ResX x $ResY), $Frames frames"
Write-Host "log     : $Log"
Write-Host "output  : $OutDir"
Write-Host "host    : $Editor"

$process = Start-Process -FilePath $Editor -ArgumentList $arguments -PassThru
Write-Host "started pid $($process.Id)"
if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    Write-Warning "still running after $TimeoutSeconds s; leaving it alone"
    exit 2
}
Write-Host "exit code: $($process.ExitCode)"

# Newest capture produced by this run. UE writes to the engine-level profiling
# directory unless the project has its own override, so check both.
$searchDirs = @(
    (Join-Path $ProjectRoot "Saved/Profiling/CSV"),
    (Join-Path $env:LOCALAPPDATA "UnrealEngine/5.8/Saved/Profiling/CSV")
)
$csv = $null
foreach ($dir in $searchDirs) {
    if (-not (Test-Path $dir)) { continue }
    $candidate = Get-ChildItem $dir -Filter "Profile(*).csv" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -ge $started } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($candidate) { $csv = $candidate; break }
}
if (-not $csv) {
    Write-Warning "no CSV newer than $started in: $($searchDirs -join ', ')"
    exit 3
}
$target = Join-Path $OutDir "baseline.csv"
Copy-Item $csv.FullName $target -Force
Write-Host "capture : $($csv.FullName)"
Write-Host "copied  : $target"
Get-ChildItem $OutDir -File | Select-Object Name, Length | Format-Table -AutoSize