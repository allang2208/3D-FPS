$ErrorActionPreference = 'Stop'
$taskProject = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskEngine = 'E:/Program Files (x86)/UE_5.8'
$taskProcesses = @(Get-CimInstance Win32_Process)
$taskEditors = @($taskProcesses | Where-Object {
    $_.Name -like 'UnrealEditor*.exe' -and
    ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
})
if ($taskEditors.Count) { throw 'Close the FPSGAME editor before building. No processes were stopped.' }
$taskBuilders = @($taskProcesses | Where-Object {
    $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
})
if ($taskBuilders.Count) { throw 'A native build is active; wait for it to finish before submitting this build.' }
$taskDll = Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
if (Test-Path -LiteralPath $taskDll) {
    $taskFile = [IO.File]::Open($taskDll, 'Open', 'ReadWrite', 'None')
    $taskFile.Dispose()
}
$taskLogDir = Join-Path $taskProject 'Saved/BuildEditor'
New-Item -ItemType Directory -Path $taskLogDir -Force | Out-Null
$taskLog = Join-Path $taskLogDir ('dungeon-streaming-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$taskReceipt = Join-Path $PSScriptRoot 'build-receipt.json'
# Use ordinary dependency tracking: the generator header changed. Do not use
# -NoUBTMakefiles, hot-reload module suffixes, or a test/PIE command.
& (Join-Path $taskEngine 'Engine/Build/BatchFiles/Build.bat') FPSGAMEEditor Win64 Development `
    "-Project=$(Join-Path $taskProject 'FPSGAME.uproject')" -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog"
$taskCode = $LASTEXITCODE
@{ target='FPSGAMEEditor'; exit_code=$taskCode; log=$taskLog; tests_run=$false; game_run=$false } |
    ConvertTo-Json | Set-Content -LiteralPath $taskReceipt -Encoding utf8
if ($taskCode -ne 0) { throw "Dungeon optimization build failed: $taskLog" }
Write-Output "DUNGEON_OPTIMIZATION_BUILT $taskLog"
