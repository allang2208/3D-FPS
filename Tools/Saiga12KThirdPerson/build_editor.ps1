$ErrorActionPreference='Stop'
$inspectRoot='D:/FPS3D/FPSGAME'
$inspectOut="$inspectRoot/SourceAssets/Saiga12KThirdPerson20261018/Receipts"
while(@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}).Count -gt 0){Start-Sleep -Seconds 10}
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Editor reopened; preserve its active state.'}
$inspectFlags=@()
$inspectRc="$inspectRoot/Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/Default.rc2.res.rsp"
if((Test-Path -LiteralPath $inspectRc) -and ((Get-Content -LiteralPath $inspectRc -Raw) -match 'WITH_LIVE_CODING=0')){$inspectFlags+='-NoLiveCoding'}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$inspectRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE @inspectFlags -NoUBA -NoUBTMakefiles -MaxParallelActions=4 -WaitMutex "-Log=$inspectOut/build-editor.log" *> "$inspectOut/build-editor-console.log"
$inspectExit=$LASTEXITCODE
@{target='FPSGAMEEditor';exit_code=$inspectExit;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$inspectOut/build-editor.json" -Encoding utf8
exit $inspectExit
