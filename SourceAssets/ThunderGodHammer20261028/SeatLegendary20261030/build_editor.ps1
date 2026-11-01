$ErrorActionPreference='Stop'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskEditor=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^UnrealEditor' -and ((-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject') })
if($taskEditor.Count -gt 0){throw 'Preserve the running editor/commandlet; full DLL build requires it to finish or close.'}
while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool.dll'}).Count -gt 0){Start-Sleep -Seconds 5}
$taskLog=Join-Path $PSScriptRoot ('build-'+$taskStamp+'.log')
$taskOutput=Join-Path $PSScriptRoot ('build-'+$taskStamp+'-console.log')
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$taskLog" *> $taskOutput
$taskCode=$LASTEXITCODE
[ordered]@{target='FPSGAMEEditor';exit_code=$taskCode;log=$taskLog;finished=(Get-Date).ToString('o');gameplay_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot ('build-'+$taskStamp+'-receipt.json')) -Encoding utf8
Get-Content -LiteralPath $taskOutput -Tail 15
exit $taskCode
