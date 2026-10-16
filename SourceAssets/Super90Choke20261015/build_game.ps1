$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME/SourceAssets/Super90Choke20261015'
$deadline = [DateTime]::UtcNow.AddMinutes(10)
while ($true) {
    $building = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='UnrealBuildTool.exe'") | Where-Object { $_.CommandLine -match 'UnrealBuildTool' }
    if (-not $building) { break }
    if ([DateTime]::UtcNow -ge $deadline) { Write-Output 'EXISTING_BUILD_STILL_ACTIVE'; exit 75 }
    Start-Sleep -Seconds 10
}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskRoot/build_game.log"
$resultCode = $LASTEXITCODE
@{ target='FPSGAME Win64 Development'; exitCode=$resultCode; runtimeTested=$false } | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build_game_receipt.json" -Encoding utf8
exit $resultCode
