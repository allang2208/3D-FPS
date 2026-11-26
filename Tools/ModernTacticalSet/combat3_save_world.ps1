$ErrorActionPreference='Stop'
$r3Tools='D:/FPS3D/FPSGAME/Tools/ModernTacticalSet'
$r3Root='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3'
$env:TS01_SHIRT_SAVE_PLAN="$r3Root/authored-world.json"
for($r3Batch=0;$r3Batch -lt 9;$r3Batch++){
    & "$r3Tools/run_asset.ps1" -Script combat3_save_world.py -ReceiptName ('combat3-world-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    if($LASTEXITCODE -ne 0){throw 'Garment asset production stopped; prior saves retained'}
    $r3Saved=Get-Content -LiteralPath "$r3Root/saved.json" -Raw | ConvertFrom-Json
    if($r3Saved.completed){break}
}
if(-not $r3Saved.completed){throw 'World garments remain incomplete'}
Remove-Item Env:TS01_SHIRT_SAVE_PLAN
& "$r3Tools/run_asset.ps1" -Script combat3_save_artwork.py -ReceiptName ('combat3-art-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
exit $LASTEXITCODE
