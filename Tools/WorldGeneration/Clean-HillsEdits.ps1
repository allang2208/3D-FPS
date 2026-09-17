param(
    [string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8',
    [int]$StartupTimeoutSeconds = 420
)

# Authoring helper: launch the editor, clear the hills world's runtime terrain edits
# (keeping Seed/WorldId) and verify the map holds no voxel-era actors, then quit.
# It edits the save slot and reads one map; it runs no gameplay or acceptance test.
$ErrorActionPreference = 'Continue'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$editor = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor.exe'
$projectFile = Join-Path $projectRoot 'FPSGAME.uproject'
$client = Join-Path $projectRoot 'Tools/AssetPipeline/ue_python_exec.py'
$script = Join-Path $PSScriptRoot 'clean_hills_edits.py'

if (@(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'UnrealEditor is already running; close it before running this helper.'
}

$process = Start-Process $editor -ArgumentList @($projectFile, '-NoSplash') -WindowStyle Hidden -PassThru
Write-Output "editor pid=$($process.Id), waiting for the remote execution node"

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
$node = $false
while (-not $node -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 15
    $list = & python $client --list 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0 -and $list -match 'project=FPSGAME') { $node = $true }
}
if (-not $node) { throw "no FPSGAME editor node appeared within $StartupTimeoutSeconds s" }

& python $client --script $script
$scriptExit = $LASTEXITCODE

& python $client --statement "import unreal; unreal.SystemLibrary.quit_editor()" | Out-Null
Write-Output "restore script exit=$scriptExit; editor quit requested"
exit $scriptExit
