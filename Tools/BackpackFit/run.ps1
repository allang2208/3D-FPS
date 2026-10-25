param([string]$Revision=('Clothing_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')),[switch]$AuthorOnly,[switch]$ResumeSave)
$ErrorActionPreference='Stop'
$fitProject='D:/FPS3D/FPSGAME'
if($Revision -notmatch '^[A-Za-z0-9_-]+$'){throw 'Invalid fit revision'}
$fitRoot=Join-Path $fitProject ('SourceAssets/BackpackFit20261024/'+$Revision)
$env:BACKPACK_FIT_RUN_DIR=$fitRoot
$fitBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$fitStage=Join-Path $fitProject 'Tools/BackpackFit/run_stage.ps1'
if(-not $ResumeSave){
    & python (Join-Path $fitProject 'Tools/BackpackFit/pending.py')
    if($LASTEXITCODE -ne 0){throw 'Backpack native input preparation failed'}
    $fitPending=Get-Content -LiteralPath (Join-Path $fitRoot 'pending.json') -Raw | ConvertFrom-Json
    if($fitPending.count -eq 0){Write-Output 'Backpack recipes are current; no asset work needed.';exit 0}
    & $fitStage -Stage capture -Revision $Revision -NullRHI
    if($LASTEXITCODE -ne 0){throw 'Backpack source capture stopped'}
    & python (Join-Path $fitProject 'Tools/BackpackFit/classify_cargo.py')
    if($LASTEXITCODE -ne 0){throw 'Backpack cargo/strap separation stopped'}
    foreach($fitScript in @('surfaces','sample_shells')){
        & $fitBlender -b -t 6 --python-exit-code 1 --python (Join-Path $fitProject ('Tools/BackpackFit/'+$fitScript+'.py')) *> (Join-Path $fitRoot ($fitScript+'.log'))
        if($LASTEXITCODE -ne 0){throw ('Backpack authoring stopped: '+$fitScript)}
    }
    & python (Join-Path $fitProject 'Tools/BackpackFit/author_contact.py') *> (Join-Path $fitRoot 'author.log')
    if($LASTEXITCODE -ne 0){throw 'Backpack contact authoring stopped'}
}
if($AuthorOnly){Write-Output 'Backpack sources authored; assets not published.';exit 0}
$fitAuthored=Get-Content -LiteralPath (Join-Path $fitRoot 'authored.json') -Raw | ConvertFrom-Json
$fitBatchSize=if($env:BACKPACK_FIT_BATCH_SIZE){[int]$env:BACKPACK_FIT_BATCH_SIZE}else{24}
for($fitBatch=0;$fitBatch -le [Math]::Ceiling(($fitAuthored.rows.Count+$fitAuthored.statics.Count)/$fitBatchSize);$fitBatch++){
    & $fitStage -Stage save_assets -Revision $Revision -NewRevisionOnly -NullRHI
    if($LASTEXITCODE -ne 0){throw 'Backpack save stopped; resume the same revision with -ResumeSave'}
    $fitSaved=Get-Content -LiteralPath (Join-Path $fitRoot 'saved_assets.json') -Raw | ConvertFrom-Json
    if($fitSaved.completed){break}
}
if(-not $fitSaved.completed){throw 'Backpack assets remain incomplete'}
& python (Join-Path $fitProject 'Tools/BackpackFit/publish.py')
if($LASTEXITCODE -ne 0){throw 'Backpack scoped publication stopped'}
& python (Join-Path $fitProject 'Tools/BackpackFit/register.py')
if($LASTEXITCODE -ne 0){throw 'Backpack dependency receipt stopped'}
Write-Output 'Backpack assets saved and integrated. No gameplay tests or editor launch.'
