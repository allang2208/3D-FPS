$ErrorActionPreference='Stop'
while($taskActive=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat')})) {
    Write-Output 'Waiting for the current native build.'
    foreach($taskProcess in $taskActive){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
}
if(Get-Process FPSGAME -ErrorAction SilentlyContinue){throw 'Preserve the running standalone game before linking.'}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=6 *> "$PSScriptRoot/build-FPSGAME.log"
$taskExit=$LASTEXITCODE
@{target='FPSGAME';exit_code=$taskExit;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build-game-receipt.json" -Encoding utf8
Get-Content -LiteralPath "$PSScriptRoot/build-FPSGAME.log" -Tail 12
exit $taskExit
