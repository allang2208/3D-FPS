$ErrorActionPreference='Stop'
$surfaceRoot='D:/FPS3D/FPSGAME'
$surfaceOut="$surfaceRoot/SourceAssets/Saiga12KDetail20261018/Receipts"
$surfaceBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$surfaceReceipts=@()
foreach($surfaceTarget in @('FPSGAME','FPSGAMEEditor')) {
 if($surfaceTarget -eq 'FPSGAMEEditor') {
  while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') }).Count -gt 0) { Start-Sleep -Seconds 10 }
 }
 while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') }).Count -gt 0) { Start-Sleep -Seconds 10 }
 $surfaceLog="$surfaceOut/build-$surfaceTarget.log"
 & $surfaceBuild $surfaceTarget Win64 Development "-Project=$surfaceRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 -WaitMutex "-Log=$surfaceLog" *> "$surfaceOut/build-$surfaceTarget-console.log"
 $surfaceCode=$LASTEXITCODE
 $surfaceReceipts+=@{target=$surfaceTarget;exit_code=$surfaceCode;log=$surfaceLog;completed=(Get-Date).ToString('o');runtime_tested=$false}
 $surfaceReceipts | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$surfaceOut/build.json" -Encoding utf8
 if($surfaceCode -ne 0){throw "$surfaceTarget build failed: $surfaceCode"}
}
