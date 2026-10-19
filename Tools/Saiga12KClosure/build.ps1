$ErrorActionPreference='Stop'
$closureRoot='D:/FPS3D/FPSGAME'
$closureOut="$closureRoot/SourceAssets/Saiga12KClosure20261018/Receipts"
$closureResults=@()
foreach($closureTarget in @('FPSGAME','FPSGAMEEditor')){
 while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($closureTarget -eq 'FPSGAMEEditor' -and $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')) }).Count -gt 0){Start-Sleep -Seconds 10}
 # Match the current compiled feature layout. Changing WITH_LIVE_CODING invalidates
 # every object even when no hot reload or Live Coding session is requested.
 $closureLayoutFlags=@()
 $closureRc="$closureRoot/Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/Default.rc2.res.rsp"
 if($closureTarget -eq 'FPSGAMEEditor' -and (Test-Path -LiteralPath $closureRc) -and ((Get-Content -LiteralPath $closureRc -Raw) -match 'WITH_LIVE_CODING=0')){$closureLayoutFlags+='-NoLiveCoding'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $closureTarget Win64 Development "-Project=$closureRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE @closureLayoutFlags -NoUBTMakefiles -NoUBA -MaxParallelActions=4 -WaitMutex "-Log=$closureOut/build-$closureTarget.log" *> "$closureOut/build-$closureTarget-console.log"
 $closureExit=$LASTEXITCODE;$closureResults+=@{target=$closureTarget;exit_code=$closureExit;completed=(Get-Date).ToString('o')}
 $closureResults | ConvertTo-Json | Set-Content -LiteralPath "$closureOut/build.json" -Encoding utf8
 if($closureExit -ne 0){throw "$closureTarget failed: $closureExit"}
}
