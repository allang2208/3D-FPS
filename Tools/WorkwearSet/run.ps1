param([switch]$AuthorOnly,[switch]$ResumeSave)
$ErrorActionPreference='Stop'
$workwearProject='D:/FPS3D/FPSGAME'
$workwearRoot=Join-Path $workwearProject 'SourceAssets/WorkwearSet20261024'
$workwearStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$workwearRunner=Join-Path $workwearProject 'Tools/WorkwearSet/run_asset.ps1'
$workwearBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
if(-not $ResumeSave){
    & py -3.11 (Join-Path $workwearProject 'Tools/WorkwearSet/prepare.py')
    if($LASTEXITCODE -ne 0){throw 'Workwear input preparation stopped.'}
    & py -3.11 (Join-Path $workwearProject 'Tools/WorkwearSet/make_textures.py')
    if($LASTEXITCODE -ne 0){throw 'Workwear surface production stopped.'}
    foreach($workwearScript in @('author_hat.py','author_jacket.py')){
        & $workwearBlender -b --factory-startup -t 6 --python-exit-code 1 --python (Join-Path $workwearProject ('Tools/WorkwearSet/'+$workwearScript)) *> (Join-Path $workwearRoot ('Logs/'+$workwearScript+'-'+$workwearStamp+'.log'))
        if($LASTEXITCODE -ne 0){throw ('Workwear authoring stopped: '+$workwearScript)}
    }
    & py -3.11 (Join-Path $workwearProject 'Tools/WorkwearSet/fit_kaitlin.py')
    if($LASTEXITCODE -ne 0){throw 'Kaitlin authoring stopped.'}
    & $workwearBlender -b --factory-startup -t 6 --python-exit-code 1 --python (Join-Path $workwearProject 'Tools/WorkwearSet/export_jacket.py') *> (Join-Path $workwearRoot ('Logs/export-'+$workwearStamp+'.log'))
    if($LASTEXITCODE -ne 0){throw 'Workwear export stopped.'}
}
if($AuthorOnly){Write-Output 'Workwear sources authored; no asset publication.';exit 0}
& $workwearRunner -Script 'save_hat.py' -ReceiptName ('workwear-hat-'+$workwearStamp)
if($LASTEXITCODE -ne 0){throw 'Boonie asset save stopped.'}
for($workwearBatch=0;$workwearBatch -lt 9;$workwearBatch++){
    & $workwearRunner -Script 'save_assets.py' -ReceiptName ('workwear-jacket-'+$workwearStamp+'-'+$workwearBatch)
    if($LASTEXITCODE -ne 0){throw 'Jacket save stopped; retain completed packages.'}
    $workwearSaved=Get-Content -LiteralPath (Join-Path $workwearRoot 'saved_assets.json') -Raw | ConvertFrom-Json
    if($workwearSaved.completed){break}
}
if(-not $workwearSaved.completed){throw 'Jacket asset save incomplete.'}
& $workwearRunner -Script 'save_display.py' -ReceiptName ('workwear-display-'+$workwearStamp)
if($LASTEXITCODE -ne 0){throw 'Display save stopped.'}
& py -3.11 (Join-Path $workwearProject 'Tools/WorkwearSet/publish.py')
if($LASTEXITCODE -ne 0){throw 'Scoped publication stopped.'}
