$ErrorActionPreference='Stop'
$cuffTools='D:/FPS3D/FPSGAME/Tools/ModernTacticalSet'
$cuffRoot='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1'
for($cuffBatch=0;$cuffBatch -lt 6;$cuffBatch++){
    & "$cuffTools/run_asset.ps1" -Script combat3_cuff_capture.py -ReceiptName ('combat3-cuff-native-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    if($LASTEXITCODE -ne 0){throw 'Current native cuff capture stopped'}
    $cuffState=Get-Content -LiteralPath "$cuffRoot/captured.json" -Raw | ConvertFrom-Json
    if($cuffState.completed){break}
}
if(-not $cuffState.completed){throw 'Current native sources incomplete'}
