param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$slagOutput = $PSScriptRoot
$slagProjectRoot = [IO.Path]::GetFullPath((Join-Path $slagOutput '../../..'))
$slagDeadline = (Get-Date).AddMinutes(40)
# Wait for existing UBT jobs before submitting a build to the engine-wide mutex.
while ($true) {
    $slagExistingBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {
        $_.CommandLine -match 'UnrealBuildTool'
    })
    if ($slagExistingBuilds.Count -eq 0) { break }
    if ((Get-Date) -ge $slagDeadline) { throw 'Existing builds still running; none were interrupted.' }
    Start-Sleep -Seconds 15
}
$slagConsole = Join-Path $slagOutput ('build-console-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
& (Join-Path $slagProjectRoot 'Tools/Build/Build-Editor.ps1') -EngineRoot $EngineRoot *> $slagConsole
$slagLines = Get-Content -LiteralPath $slagConsole
$slagLogMarker = $slagLines | Where-Object { $_ -match 'Editor modules built.*Log: ' } | Select-Object -Last 1
if (-not $slagLogMarker) { throw "Build did not complete: $slagConsole" }
$slagBuildLog = $slagLogMarker -replace '^.*Log: ', ''
$slagDll = Get-Item -LiteralPath (Join-Path $slagProjectRoot 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
@{
    revision = 'RagdollGroundV17'; status = 'Succeeded'; target = 'FPSGAMEEditor Win64 Development'
    build_log = $slagBuildLog; build_console = $slagConsole
    dll = $slagDll.FullName; dll_last_write_time = $slagDll.LastWriteTime.ToString('o')
    runtime_tested = $false; editor_started = $false; pie_started = $false
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $slagOutput 'build_installation.json') -Encoding UTF8
Write-Output "SLAG_V17_EDITOR_BUILT $slagBuildLog"
