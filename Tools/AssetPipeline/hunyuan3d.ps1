# Stable entry point: avoid WindowsApps Python's redirected local-app-data view.
$ErrorActionPreference = 'Stop'
$pythonExe = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python311/python.exe'
if (!(Test-Path -LiteralPath $pythonExe)) { throw 'Python 3.11 executable missing; use hunyuan3d.py with your Python runtime.' }
& $pythonExe (Join-Path $PSScriptRoot 'hunyuan3d.py') @args
exit $LASTEXITCODE
