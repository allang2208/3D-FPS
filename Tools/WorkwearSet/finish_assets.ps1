param([int]$FirstBatch=2)
$ErrorActionPreference='Stop'
$workwearProject='D:/FPS3D/FPSGAME'
$workwearStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
for($workwearBatch=$FirstBatch;$workwearBatch -lt 12;$workwearBatch++){
    & (Join-Path $workwearProject 'Tools/WorkwearSet/run_asset.ps1') -Script 'save_assets.py' -ReceiptName ('workwear-save-'+$workwearStamp+'-'+$workwearBatch)
    if($LASTEXITCODE -ne 0){throw 'Workwear asset batch stopped; resume from saved packages.'}
    $workwearSaved=Get-Content -LiteralPath (Join-Path $workwearProject 'SourceAssets/WorkwearSet20261024/saved_assets.json') -Raw | ConvertFrom-Json
    if($workwearSaved.completed){break}
}
if(-not $workwearSaved.completed){throw 'Workwear garment save incomplete.'}
& (Join-Path $workwearProject 'Tools/WorkwearSet/run_asset.ps1') -Script 'save_hat.py' -ReceiptName ('workwear-hat-metric-'+$workwearStamp)
if($LASTEXITCODE -ne 0){throw 'Workwear hat metric-surface save stopped.'}
& (Join-Path $workwearProject 'Tools/WorkwearSet/run_asset.ps1') -Script 'save_display.py' -ReceiptName ('workwear-display-'+$workwearStamp)
if($LASTEXITCODE -ne 0){throw 'Workwear display save stopped.'}
& py -3.11 (Join-Path $workwearProject 'Tools/WorkwearSet/publish.py')
if($LASTEXITCODE -ne 0){throw 'Workwear scoped publication stopped.'}
