$ErrorActionPreference='Stop'
$recallStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$recallEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
if($recallEditor.Count -gt 0){throw 'An editor is open; preserve it and apply this cpp-only change through that editor.'}
$recallLog=Join-Path $PSScriptRoot ('build-'+$recallStamp+'.log')
$recallOutput=Join-Path $PSScriptRoot ('build-'+$recallStamp+'-console.log')
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$recallLog" *> $recallOutput
$recallCode=$LASTEXITCODE
[ordered]@{target='FPSGAMEEditor';exit_code=$recallCode;log=$recallLog;finished=(Get-Date).ToString('o');gameplay_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot ('build-'+$recallStamp+'-receipt.json')) -Encoding utf8
Get-Content -LiteralPath $recallOutput -Tail 12
if($recallCode -ne 0){exit $recallCode}
& (Join-Path $PSScriptRoot 'publish_assets.ps1')
exit $LASTEXITCODE
