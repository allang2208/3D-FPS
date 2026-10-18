$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/BowConsumableHandoff20261018'
& (Join-Path $taskRoot 'build.ps1') -Target Game -MaxParallelActions 4
if($LASTEXITCODE -ne 0){throw "Game build stopped with exit $LASTEXITCODE"}
& (Join-Path $taskRoot 'build.ps1') -Target Editor -MaxParallelActions 4 -IsolatedEditorPids @(93428)
if($LASTEXITCODE -ne 0){throw "Editor build stopped with exit $LASTEXITCODE"}
& (Join-Path $taskRoot 'save-delivery.ps1')
