$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskOther=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })
foreach($taskProcess in $taskOther){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
if(Get-CimInstance Win32_Process -Filter "Name='FPSGAME.exe'"){throw 'Preserve running FPSGAME.exe.'}
$env:UE_SKIP_UBT_SDK_SETUP='1'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAME Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -NoHotReloadFromIDE *> (Join-Path $taskRoot 'build-FPSGAME.log')
$taskExit=$LASTEXITCODE
@{target='FPSGAME';exit_code=$taskExit;log=(Join-Path $taskRoot 'build-FPSGAME.log');finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'build-game-receipt.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $taskRoot 'build-FPSGAME.log') -Tail 18
exit $taskExit
