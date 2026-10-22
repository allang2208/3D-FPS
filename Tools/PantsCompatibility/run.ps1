param([switch]$AuthorOnly)
$ErrorActionPreference='Stop'
$fitProject='D:/FPS3D/FPSGAME'
$fitRoot=Join-Path $fitProject 'SourceAssets/PantsCompatibility20261022'
$fitStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$fitRunner=Join-Path $fitProject 'Tools/FieldRangerTop/run_asset.ps1'
$fitBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
& python (Join-Path $fitProject 'Tools/PantsCompatibility/inventory.py')
if($LASTEXITCODE -ne 0){throw 'Pants inventory could not be prepared.'}
& $fitRunner -Script '../PantsCompatibility/capture.py' -ReceiptName ('pants-fit-capture-'+$fitStamp)
if($LASTEXITCODE -ne 0){throw 'Saved waist capture could not finish.'}
foreach($fitScript in @('author.py','author_default.py')){
    & $fitBlender -b -t 6 --python-exit-code 1 --python (Join-Path $fitProject ('Tools/PantsCompatibility/'+$fitScript)) *> (Join-Path $fitRoot ($fitStamp+'-'+$fitScript+'.log'))
    if($LASTEXITCODE -ne 0){throw ('Pants fit authoring failed: '+$fitScript)}
}
if($AuthorOnly){Write-Output 'Pants fit sources ready; no asset publication requested.';exit 0}
$fitManifest=Get-Content -LiteralPath (Join-Path $fitRoot 'authored.json') -Raw | ConvertFrom-Json
for($fitBatch=0;$fitBatch -lt ($fitManifest.records.Count+1);$fitBatch++){
    & $fitRunner -Script '../PantsCompatibility/save.py' -ReceiptName ('pants-fit-save-'+$fitStamp+'-'+$fitBatch)
    if($LASTEXITCODE -ne 0){throw 'Pants fit save stopped; retain existing assets and resume after the reported issue.'}
    $fitSaved=Get-Content -LiteralPath (Join-Path $fitRoot 'saved_assets.json') -Raw | ConvertFrom-Json
    if($fitSaved.completed){break}
}
if(-not $fitSaved.completed){throw 'Pants fit assets are incomplete; configuration not changed.'}
& python (Join-Path $fitProject 'Tools/PantsCompatibility/publish.py')
if($LASTEXITCODE -ne 0){throw 'Pants fit configuration was not published.'}
Write-Output 'Pants compatibility assets and configuration saved; gameplay acceptance remains user-side.'
