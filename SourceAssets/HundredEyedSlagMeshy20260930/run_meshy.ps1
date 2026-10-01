param(
    [ValidateSet('build', 'status', 'balance')]
    [string]$Command = 'build'
)
$ErrorActionPreference = 'Stop'
$TaskPython = 'E:\无尽轮回\长期备份\2026-7-13-1\ComfyUI\.venv\Scripts\python.exe'
& $TaskPython (Join-Path $PSScriptRoot 'meshy_pipeline.py') $Command
exit $LASTEXITCODE
