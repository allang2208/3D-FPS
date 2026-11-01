$ErrorActionPreference = 'Stop'
$taskRoot='D:/FPS3D/FPSGAME'
if (@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'").Count -gt 0) {throw 'Editor is running; full native build requires its binaries. Preserved editor.'}
while (@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll') -or $_.Name -eq 'UnrealEditor-Cmd.exe'}).Count -gt 0) {Start-Sleep -Seconds 5}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE *> (Join-Path $PSScriptRoot 'build.log')
$taskExit=$LASTEXITCODE
@{exit_code=$taskExit;target='FPSGAMEEditor Win64 Development';runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
exit $taskExit
