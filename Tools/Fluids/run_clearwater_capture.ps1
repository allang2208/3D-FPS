# Render the Clearwater test level and capture a screenshot from a warm frame.
#
# Why this exists: `-ExecCmds="HighResShot"` fires on the very first frame, while the map is
# still streaming and the shot comes back as literal pure black (max pixel 0.00000) that looks
# exactly like an unlit scene. That false negative cost a full diagnosis round.
#
# Two mechanisms that do NOT work in this environment, recorded so nobody re-tries them:
#   * AClearwaterWater's `-ClearwaterShot=N` timer never fires here (the tick hook is not
#     reached before the process is torn down), so the "wait N seconds then shoot" path is dead.
#   * `-ExecCmds="quit"` runs from the engine startup queue, i.e. before gameplay, so it kills
#     the process mid-stream. The engine stays up far longer than the capture needs.
# What does work is letting the engine idle, then issuing the shot through the game's own
# exec queue, and bounding the run with this script's own timeout.
#
# `-ClearwaterNoMenu` is required: without it the startup mode menu covers the viewport and
# every screenshot is a picture of the menu. It is implemented in FPSGAMEPlayerController.cpp.
#
#     powershell -File Tools/Fluids/run_clearwater_capture.ps1
#     powershell -File Tools/Fluids/run_clearwater_capture.ps1 -Warmup 15 -ResX 1920 -ResY 1080
#
# Output goes to Saved/Screenshots/WindowsEditor/ with the engine's own numbering
# (ScreenShot00000.png ...); the newest file newer than this run's start time is reported.
[CmdletBinding()]
param(
    [string]$Map = "/Game/Clearwater/L_ClearwaterWater",
    [int]$Warmup = 12,
    [int]$ResX = 1280,
    [int]$ResY = 720,
    [int]$TimeoutSeconds = 300,
    [string]$Tag = "clearwater",
    # Report the resolved command line and exit without launching the engine.
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$Project = Join-Path $ProjectRoot "FPSGAME.uproject"
$Editor = "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
$ShotDir = Join-Path $ProjectRoot "Saved/Screenshots/WindowsEditor"
$Log = Join-Path $ProjectRoot "Saved/Logs/$Tag`_capture.log"

if (-not (Test-Path $Editor)) { throw "editor not found: $Editor" }
if (-not (Test-Path $Project)) { throw "project not found: $Project" }
if (-not (Test-Path $ShotDir)) { New-Item -ItemType Directory -Force -Path $ShotDir | Out-Null }

# The engine needs a moment to stream and to finish shader/texture work before the shot is
# meaningful; `Shot showui` keeps the HUD so the capture matches what the player sees.
$arguments = @(
    "`"$Project`""
    $Map
    "-game"
    "-RenderOffscreen"
    "-unattended"
    "-nosplash"
    "-nosound"
    "-ClearwaterNoMenu"
    "-ResX=$ResX"
    "-ResY=$ResY"
    "-ExecCmds=`"Shot showui`""
    "-abslog=`"$Log`""
)

Write-Host "map     : $Map"
Write-Host "resolve : ${ResX}x${ResY}"
Write-Host "warmup  : $Warmup s before the shot is issued"
Write-Host "shots   : $ShotDir"
Write-Host "log     : $Log"

if ($DryRun) {
    Write-Host ""
    Write-Host "would run:"
    Write-Host "  $Editor $($arguments -join ' ')"
    exit 0
}

$before = Get-Date
$process = Start-Process -FilePath $Editor -ArgumentList $arguments -PassThru
Write-Host "started pid $($process.Id); engine is not told to quit, this script bounds the run"

# The shot is issued by the game's exec queue once it is up; the warm-up is applied by
# waiting before we go looking for the file rather than by any engine-side timer.
Start-Sleep -Seconds $Warmup

$deadline = $before.AddSeconds($TimeoutSeconds)
$shot = $null
while ((Get-Date) -lt $deadline) {
    $shot = Get-ChildItem $ShotDir -Filter 'ScreenShot*.png' -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt $before } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($shot) { break }
    Start-Sleep -Seconds 2
}

if (-not $process.HasExited) {
    Write-Host "stopping pid $($process.Id)"
    Stop-Process -Id $process.Id -Force
    Start-Sleep -Seconds 3
} else {
    Write-Host "engine exited on its own, code $($process.ExitCode)"
}

if (-not $shot) {
    Write-Warning "no new screenshot in $ShotDir; check $Log"
    exit 2
}
Write-Host "screenshot: $($shot.FullName)  $([math]::Round($shot.Length/1KB,1)) KB"
Write-Host "verify it is not black before drawing conclusions: a pure-black frame means the"
Write-Host "shot landed too early, not that the scene is unlit."
exit 0
