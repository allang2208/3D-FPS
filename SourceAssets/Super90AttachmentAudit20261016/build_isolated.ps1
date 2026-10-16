$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/Super90AttachmentAudit20261016'
$deadline=[DateTime]::UtcNow.AddMinutes(30)
while([DateTime]::UtcNow -lt $deadline){
    $busy=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='UnrealBuildTool.exe'") | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}
    if(-not $busy){break}
    $observed=Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue
    if($observed){[void]$observed.WaitForExit(10000)}
}
if($busy){exit 75}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/ShotgunAttachmentAudit20261016/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=3 "-Log=$taskRoot/isolated_editor_build.log"
$code=$LASTEXITCODE
@{exitCode=$code;target='FPSGAMEEditor Win64 Development';project='D:/FPS3D/ShotgunAttachmentAudit20261016/FPSGAME.uproject'} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/isolated_build_receipt.json" -Encoding utf8
exit $code
