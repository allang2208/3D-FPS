$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$log = Join-Path $PSScriptRoot 'game_build.log'
$activeBuilds = @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" |
    Where-Object { $_.CommandLine -match 'FPSGAME|UnrealBuildTool' })
if ($activeBuilds.Count -gt 0) { Write-Output 'A build is still active; no overlapping build started.'; exit 2 }
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -NoLiveCoding -NoHotReload -NoHotReloadFromIDE "-Log=$log"
$result = $LASTEXITCODE
@{ target='FPSGAME Win64 Development'; exit_code=$result; log=$log; tests_run=$false } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'game_build_receipt.json') -Encoding UTF8
exit $result
