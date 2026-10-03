$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$buildBatch = 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$buildLog = Join-Path $PSScriptRoot 'skill_game_build.log'
# Existing UBT work owns the shared object outputs. Wait without taking its mutex.
while (@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" |
    Where-Object { $_.CommandLine -match 'FPSGAME|UnrealBuildTool' }).Count -gt 0) {
    Start-Sleep -Seconds 15
}
& $buildBatch FPSGAME Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles "-Log=$buildLog"
$buildExit = $LASTEXITCODE
@{ target='FPSGAME Win64 Development'; exit_code=$buildExit; log=$buildLog; tests_run=$false } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'skill_game_build_receipt.json') -Encoding UTF8
exit $buildExit
