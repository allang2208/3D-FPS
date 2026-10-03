# Standalone (-game) CSV capture runner.
#
# The editor build cannot be relinked while an interactive editor holds
# UnrealEditor-FPSGAME.dll, but the FPSGAME target links independently and runs
# the same gameplay code. This runs that binary for measurements and validation
# that do not need the editor.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_standalone_capture.ps1 `
#     -Profile MyProbe -Map DayNight_Lighting -Frames 900 `
#     -ExtraArgs '-ExecCmds=fpssyncload 25'

param(
    [string]$Profile = "StandaloneProbe",
    [string]$Map = "DayNight_Lighting",
    [int]$Frames = 900,
    [int]$ResX = 1280,
    [int]$ResY = 720,
    [string]$ExtraArgs = "",
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$GameExe = Join-Path $ProjectRoot "Binaries/Win64/FPSGAME.exe"
$LogDir = Join-Path $ProjectRoot "Saved/Logs"
$OutDir = Join-Path $ProjectRoot ("Saved/" + $Profile)
$Log = Join-Path $LogDir ($Profile + ".log")

if (-not (Test-Path $GameExe)) {
    Write-Warning "standalone binary not built: $GameExe"
    Write-Warning "build it with: Build.bat FPSGAME Win64 Development -Project=<uproject>"
    exit 2
}
New-Item -ItemType Directory -Force -Path $LogDir, $OutDir | Out-Null

# -ExecCmds is comma separated and each command is trimmed, so a command taking a
# value must use '=' rather than a space separator.
$arguments = @(
    $ProjectRoot
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
if ($ExtraArgs -ne "") { $arguments += $ExtraArgs.Split("|") }

$started = Get-Date
Write-Host "profile : $Profile"
Write-Host "map     : $Map ($ResX x $ResY), $Frames frames"
Write-Host "host    : $GameExe"
Write-Host "log     : $Log"

$proc = Start-Process -FilePath $GameExe -ArgumentList $arguments -PassThru -NoNewWindow
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    Write-Warning "timed out after $TimeoutSeconds s; killing pid $($proc.Id)"
    $proc.Kill()
    exit 4
}
Write-Host "exit code: $($proc.ExitCode)"

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
Copy-Item $csv.FullName (Join-Path $OutDir "baseline.csv") -Force
Write-Host "capture : $($csv.FullName)"
Write-Host "copied  : $(Join-Path $OutDir 'baseline.csv')"