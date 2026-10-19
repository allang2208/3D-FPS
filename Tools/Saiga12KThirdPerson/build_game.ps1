$ErrorActionPreference='Stop'
$inspectProject='D:/FPS3D/FPSGAME'
$inspectOut="$inspectProject/SourceAssets/Saiga12KThirdPerson20261018/Receipts"
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$inspectProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 -WaitMutex "-Log=$inspectOut/build-game.log" *> "$inspectOut/build-game-console.log"
$inspectExit=$LASTEXITCODE
@{target='FPSGAME';exit_code=$inspectExit;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$inspectOut/build-game.json" -Encoding utf8
exit $inspectExit
