# Runs the M3 grass deform asset setup headless (footstep feedback: puff + trample decal + config).
#
# If an UnrealEditor process already holds this project, the script refuses to run: opening a second
# engine process against the same project would fight over the package files and the editor's
# in-memory copies. In that case do the asset authoring through the MCP batch bridge instead:
#
#   powershell -NoProfile -File Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript Tools/GrassDeform/setup_assets_m3.py
#
# Plan: Docs/WorldGeneration/grass-interaction-gpu-20260925.md section 5.

[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$project = 'D:\FPS3D\FPSGAME\FPSGAME.uproject'
$engine = 'E:\Program Files (x86)\UE_5.8'
$editorCmd = Join-Path $engine 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$script = Join-Path $PSScriptRoot 'setup_assets_m3.py'
$logDir = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'Saved\Logs'
$log = Join-Path $logDir 'GrassDeformM3.log'

if (-not (Test-Path -LiteralPath $project)) { throw "Project not found: $project" }
if (-not (Test-Path -LiteralPath $editorCmd)) { throw "Editor commandlet not found: $editorCmd" }
if (-not (Test-Path -LiteralPath $script)) { throw "Setup script not found: $script" }

# Detect any engine process holding this project (command line contains FPSGAME.uproject).
# Every editor binary flavour is checked, not just UnrealEditor: a DebugGame or a commandlet run
# that already holds the packages would corrupt them just the same.
$holders = @()
foreach ($name in @('UnrealEditor', 'UnrealEditor-Cmd', 'UnrealEditor-Win64-DebugGame',
                    'UnrealEditor-Win64-DebugGame-Cmd', 'UE4Editor', 'UE4Editor-Cmd')) {
    $procs = Get-CimInstance Win32_Process -Filter "Name='$name.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        if ($p.CommandLine -and $p.CommandLine -like '*FPSGAME.uproject*') {
            $holders += [pscustomobject]@{ Id = $p.ProcessId; Name = $name; CommandLine = $p.CommandLine }
        }
    }
}

if ($holders.Count -gt 0) {
    Write-Host ''
    Write-Host 'REFUSING TO RUN: this project is already held by a live engine process.' -ForegroundColor Yellow
    foreach ($h in $holders) {
        Write-Host ("  PID {0}  {1}" -f $h.Id, $h.Name) -ForegroundColor Yellow
    }
    Write-Host ''
    Write-Host 'Run the setup through the MCP batch bridge instead (it serialises access to the' -ForegroundColor Cyan
    Write-Host 'running editor), from the project root:' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  powershell -NoProfile -File Tools/AssetPipeline/mcp_call_codex.ps1 `' -ForegroundColor White
    Write-Host '    -PythonScript Tools/GrassDeform/setup_assets_m3.py' -ForegroundColor White
    Write-Host ''
    Write-Host 'Do NOT kill the editor process to free the project: it may hold unsaved work.' -ForegroundColor Cyan
    Write-Host ''
    exit 2
}

Write-Host "No engine process holds the project. Running headless M3 asset setup..." -ForegroundColor Green
Write-Host "  script: $script"
Write-Host "  log:    $log"

$arguments = @(
    "`"$project`""
    '-run=pythonscript'
    "-script=`"$script`""
    '-unattended'
    '-nosplash'
    # Asset authoring needs no rendering context; skipping it keeps this commandlet from
    # competing with any other engine process for the GPU.
    '-nullrhi'
    '-nop4'
    '-stdout'
    '-NoLogTimes'
    "-abslog=`"$log`""
)

if ($DryRun) {
    Write-Host ''
    Write-Host 'DryRun: would execute:' -ForegroundColor Cyan
    Write-Host ("  & `"$editorCmd`" " + ($arguments -join ' '))
    exit 0
}

if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

& $editorCmd @arguments
$code = $LASTEXITCODE

if ($code -ne 0) {
    Write-Host "M3 asset setup exited with code $code. See the output above and $log." -ForegroundColor Red
    exit $code
}

Write-Host 'M3 asset setup finished. Check the GRASS_DEFORM_M3_RESULT line above for the report.' -ForegroundColor Green
exit 0