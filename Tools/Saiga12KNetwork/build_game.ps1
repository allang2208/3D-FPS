$ErrorActionPreference='Stop'
$s12Root='D:/FPS3D/FPSGAME'
$s12Out="$s12Root/SourceAssets/Saiga12KNetwork20261019/Receipts"
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$s12Root/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 -WaitMutex "-Log=$s12Out/build-game.log" *> "$s12Out/build-game-console.log"
$s12Exit=$LASTEXITCODE
@{target='FPSGAME';exit_code=$s12Exit;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$s12Out/build-game.json" -Encoding utf8
exit $s12Exit
