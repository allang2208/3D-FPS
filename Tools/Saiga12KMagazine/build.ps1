$ErrorActionPreference='Stop'
$saigaRoot='D:/FPS3D/FPSGAME'
$saigaOut="$saigaRoot/SourceAssets/Saiga12KMagazine20261017/Receipts"
$saigaBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$receipts=@()
foreach($target in @('FPSGAME','FPSGAMEEditor')) {
 if($target -eq 'FPSGAMEEditor') {
  while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') }).Count -gt 0) { Start-Sleep -Seconds 10 }
 }
 $log="$saigaOut/build-$target.log"
 & $saigaBuild $target Win64 Development "-Project=$saigaRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 -WaitMutex "-Log=$log" *> "$saigaOut/build-$target-console.log"
 $code=$LASTEXITCODE
 $receipts+=@{target=$target;exit_code=$code;log=$log;completed=(Get-Date).ToString('o');runtime_tested=$false}
 $receipts | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$saigaOut/build.json" -Encoding utf8
 if($code -ne 0){throw "$target build failed: $code"}
}
