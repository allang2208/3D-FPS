$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskOther=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })
foreach($taskProcess in $taskOther){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'"){throw 'Preserve running UnrealEditor.exe.'}
$taskImports=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
foreach($taskProcess in $taskImports){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
$env:UE_SKIP_UBT_SDK_SETUP='1'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -NoHotReloadFromIDE *> (Join-Path $taskRoot 'build-FPSGAMEEditor.log')
$taskExit=$LASTEXITCODE
@{target='FPSGAMEEditor';exit_code=$taskExit;log=(Join-Path $taskRoot 'build-FPSGAMEEditor.log');finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'build-editor-receipt.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $taskRoot 'build-FPSGAMEEditor.log') -Tail 18
exit $taskExit
