$ErrorActionPreference='Stop'
# Wait for the existing native build without sending coordination messages or
# entering Build.bat's competing mutex loop. Keep the currently used build flags.
while (@(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
}).Count -gt 0) { Start-Sleep -Seconds 15 }
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -MaxParallelActions=4 -NoLiveCoding "-Log=$PSScriptRoot/build-editor.log" *> "$PSScriptRoot/build-console.log"
$code=$LASTEXITCODE
@{target='FPSGAMEEditor Win64 Development';exit_code=$code;runtime_tested=$false;log='build-editor.log'} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_receipt.json" -Encoding utf8
exit $code
