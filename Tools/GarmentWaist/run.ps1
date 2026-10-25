param([switch]$AuthorOnly,[switch]$ResumeSave)
$ErrorActionPreference='Stop'
$waistProject='D:/FPS3D/FPSGAME'
$waistRoot=Join-Path $waistProject 'SourceAssets/GarmentWaist20261023'
$waistRunner=Join-Path $waistProject 'Tools/GarmentWaist/run_asset.ps1'
$waistStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
if(-not $ResumeSave){
    & (Join-Path $waistProject 'Tools/PantsCompatibility/run.ps1') -AuthorOnly:$AuthorOnly
    if($LASTEXITCODE -ne 0){throw 'Refresh current pants guides and ranger pairs first.'}
    & $waistRunner -Script 'capture.py' -ReceiptName ('garment-waist-capture-'+$waistStamp)
    if($LASTEXITCODE -ne 0){throw 'Native garment capture failed.'}
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b -t 6 --python-exit-code 1 --python (Join-Path $waistProject 'Tools/GarmentWaist/author.py') *> (Join-Path $waistRoot ('author-'+$waistStamp+'.log'))
    if($LASTEXITCODE -ne 0){throw 'Waist authoring stopped; retain sources.'}
}
if($AuthorOnly){Write-Output 'Waist sources authored; assets not published.';exit 0}
$waistManifest=Get-Content -LiteralPath (Join-Path $waistRoot 'authored.json') -Raw | ConvertFrom-Json
for($waistBatch=0;$waistBatch -lt [Math]::Ceiling($waistManifest.records.Count/6)+1;$waistBatch++){
    & $waistRunner -Script 'save.py' -ReceiptName ('garment-waist-save-'+$waistStamp+'-'+$waistBatch)
    if($LASTEXITCODE -ne 0){throw 'Waist asset save stopped; resume from the saved receipt.'}
    $waistSaved=Get-Content -LiteralPath (Join-Path $waistRoot 'saved_assets.json') -Raw | ConvertFrom-Json
    if($waistSaved.completed){break}
}
if(-not $waistSaved.completed){throw 'Some waist assets are not saved; configuration retained.'}
& python (Join-Path $waistProject 'Tools/GarmentWaist/publish.py')
if($LASTEXITCODE -ne 0){throw 'Waist configuration was not published.'}
& (Join-Path $waistProject 'Tools/BackpackFit/run.ps1')
if($LASTEXITCODE -ne 0){throw 'Waist assets saved; backpack pairing remains incomplete.'}
