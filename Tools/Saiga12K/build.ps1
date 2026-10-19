$ErrorActionPreference='Stop'
$saigaRoot='D:/FPS3D/FPSGAME'
$saigaOut="$saigaRoot/SourceAssets/Saiga12K20261017/Receipts"
$saigaBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
while($true){
 $busy=@(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
  ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')
 })
 if($busy.Count -eq 0){break}
 Start-Sleep -Seconds 15
}
$receipts=@()
foreach($target in @('FPSGAMEEditor','FPSGAME')){
 $log="$saigaOut/build-$target.log"
 & $saigaBuild $target Win64 Development "-Project=$saigaRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 "-Log=$log"
 $code=$LASTEXITCODE
 $receipts += @{target=$target;exit_code=$code;log=$log;completed=(Get-Date).ToString('o');runtime_tested=$false}
 $receipts | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$saigaOut/build.json" -Encoding utf8
 if($code -ne 0){throw "$target build failed: $code"}
}