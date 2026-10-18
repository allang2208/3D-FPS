$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets/BowLeftCastHandoff20261018'
# These inputs were refined during the first build. Advance their timestamps
# after that build completes so every consumer uses the final header layout.
foreach($relative in @('Source/FPSGAME/Weapons/Bow/BowCastHandPose.h','Source/FPSGAME/Characters/FPSBodyBowPose.inl')){
    (Get-Item -LiteralPath (Join-Path $projectRoot $relative)).LastWriteTimeUtc=[DateTime]::UtcNow
}
& (Join-Path $taskRoot 'build.ps1') -Target Game -MaxParallelActions 4
if($LASTEXITCODE -ne 0){throw "Final Game build stopped with exit $LASTEXITCODE"}
& (Join-Path $taskRoot 'build.ps1') -Target Editor -MaxParallelActions 4
if($LASTEXITCODE -ne 0){throw "Final Editor build stopped with exit $LASTEXITCODE"}
& (Join-Path $taskRoot 'save-delivery.ps1')
