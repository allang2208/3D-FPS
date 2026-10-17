param([string]$Script = 'import_assets.py', [string]$ReceiptName = 'asset-import-01', [switch]$NewPackagesOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$batchRoot = Join-Path $projectRoot 'SourceAssets/M870FactoryIcons20261016'
$scriptFile = Join-Path $batchRoot $Script
$outputFile = Join-Path $batchRoot ($ReceiptName + '.txt')
if (Test-Path -LiteralPath $outputFile) { throw 'Use a fresh receipt name.' }
$processes = @(Get-CimInstance Win32_Process)
$editors = @($processes | Where-Object { $_.Name -eq 'UnrealEditor.exe' })
if ($editors.Count -gt 0 -and -not $NewPackagesOnly) {
    & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $scriptFile -OutputFile $outputFile -MaxOutputChars 3000
    exit $LASTEXITCODE
}
if ($NewPackagesOnly) {
    $newPackageDirectory = Join-Path $projectRoot 'Content/Items/Consumables/M870FactoryIcons20261016'
    if ((Test-Path -LiteralPath $newPackageDirectory) -or (Test-Path -LiteralPath (Join-Path $batchRoot 'ue-assets.json'))) {
        throw 'New-package mode requires an untouched output directory and no prior import receipt; use the current editor for continuation.'
    }
}
$busy = @($processes | Where-Object { $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
# Wait on the shared batch gate below; recheck live processes after acquisition.
# This task writes only its new M870FactoryIcons20261016 packages. Other commandlets
# cannot hold these never-created packages; owned-package continuation is
# guarded by the same port mutex and import receipt inside import_assets.py.
$sameBatch = @($processes | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'M870FactoryIcons20261016' })
if ($sameBatch.Count -gt 0) { Write-Output 'This batch is still running; do not replay an uncertain import.'; exit 75 }
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    $held = $gate.WaitOne([TimeSpan]::FromSeconds(60))
    if (-not $held) { Write-Output 'Asset batch queue timed out; no commandlet launched.'; exit 75 }
    $changed = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'UnrealEditor.exe' -and -not $NewPackagesOnly) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    if ($changed.Count -gt 0) { Write-Output 'Editor/build state changed while queued; no commandlet launched.'; exit 75 }
    if ($NewPackagesOnly -and ((Test-Path -LiteralPath $newPackageDirectory) -or (Test-Path -LiteralPath (Join-Path $batchRoot 'ue-assets.json')))) {
        throw 'Output ownership changed while queued; no commandlet launched.'
    }
    $commandlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $logFile = Join-Path $batchRoot ($ReceiptName + '.log')
    & $commandlet (Join-Path $projectRoot 'FPSGAME.uproject') '-run=pythonscript' "-script=$scriptFile" '-unattended' '-nop4' '-nosplash' '-nosound' '-NullRHI' "-abslog=$logFile" *> $outputFile
    $result = $LASTEXITCODE
    Write-Output "Asset commandlet exit=$result; log=$logFile"
    Get-Content -LiteralPath $outputFile -Tail 12
    exit $result
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
