$ErrorActionPreference = 'Stop'
$designSource = Join-Path $PSScriptRoot '../FreightWarehouseWeathering20261110/run_background.ps1'
$designHelperRoot = (Get-Item -LiteralPath $designSource).Directory.FullName
# Use the existing project commandlet/bridge rules. Remain queued on the same
# mutex across long active batches instead of abandoning our position every 5s.
$designRunner = (Get-Content -LiteralPath $designSource -Raw).Replace('$taskMutex.WaitOne(5000)', '$taskMutex.WaitOne()').Replace('$PSScriptRoot', '$designHelperRoot')
& ([scriptblock]::Create($designRunner)) -ScriptName '../FreightStationDesign20261112/read_inputs.py'
