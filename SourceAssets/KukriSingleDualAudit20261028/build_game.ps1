$ErrorActionPreference='Stop'
$taskRoot='D:\FPS3D\FPSGAME\SourceAssets\KukriSingleDualAudit20261028'
$taskFiles=@('FPSBodyKukriMotion.h','FPSPlayerBodyAnimInstance.h','FPSPlayerBodyAnimInstance.cpp','FPSPlayerBodyComponent.cpp','FPSPlayerBodyEquipment.cpp','FPSPlayerBodyKukri.cpp')
$taskHashes=@{}
foreach($taskFile in $taskFiles) { $taskHashes[$taskFile]=(Get-FileHash -LiteralPath (Join-Path 'D:\FPS3D\FPSGAME\Source\FPSGAME\Characters' $taskFile) -Algorithm SHA256).Hash }
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAME Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE "-Log=$taskRoot\game-build.log" 2>&1 | Out-File -LiteralPath "$taskRoot\game-build-console.log" -Encoding utf8
$taskExit=$LASTEXITCODE
[ordered]@{target='FPSGAME Win64 Development';exit_code=$taskExit;completed=(Get-Date -Format o);source_hashes=$taskHashes;runtime_tested=$false;editor_module_built=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$taskRoot\game-build-result.json" -Encoding utf8
Get-Content -LiteralPath "$taskRoot\game-build-console.log" -Tail 16
exit $taskExit