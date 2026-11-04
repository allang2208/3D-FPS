param([string]$ScriptName = 'import_blades.py', [int]$QueueWaitSeconds = 600)
$ErrorActionPreference = 'Stop'
if ($ScriptName -eq 'import_blades.py') {
    & (Join-Path $PSScriptRoot 'ContinuousBladesR5_20261104/run_import.ps1') -QueueWaitSeconds $QueueWaitSeconds
    exit $LASTEXITCODE
}
throw 'Use the current R5 serialized asset batch; standalone historical icon import is retired.'
