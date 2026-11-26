$ErrorActionPreference='Stop'
$combatTools='D:/FPS3D/FPSGAME/Tools/ModernTacticalSet'
$combatRoot='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3'
Remove-Item Env:TS01_SHIRT_SAVE_PLAN -ErrorAction SilentlyContinue
for($combatBatch=0;$combatBatch -lt 12;$combatBatch++){
    & "$combatTools/run_asset.ps1" -Script combat3_save_final.py -ReceiptName ('combat3-resume-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    if($LASTEXITCODE -ne 0){throw 'Wearable save batch stopped; retained saved receipts'}
    $combatSaved=Get-Content -LiteralPath "$combatRoot/saved.json" -Raw | ConvertFrom-Json
    if($combatSaved.completed){break}
}
if(-not $combatSaved.completed){throw 'Garment saves remain incomplete'}
if(-not(Test-Path -LiteralPath "$combatRoot/artwork-saved.json") -or -not((Get-Content -LiteralPath "$combatRoot/artwork-saved.json" -Raw | ConvertFrom-Json).completed)){
    & "$combatTools/run_asset.ps1" -Script combat3_save_artwork.py -ReceiptName ('combat3-artwork-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    if($LASTEXITCODE -ne 0){throw 'Artwork save stopped'}
}
& python -X utf8 "$combatTools/combat3_publish.py"
if($LASTEXITCODE -ne 0){throw 'Garment scoped publication stopped'}
& "$combatTools/combat3_backpack_run.ps1"
if($LASTEXITCODE -ne 0){throw 'Backpack integration stopped'}
& python -X utf8 "$combatTools/combat3_delivery.py"
exit $LASTEXITCODE
