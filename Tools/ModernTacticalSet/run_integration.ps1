param([switch]$ResumeAssets,[switch]$ResumeBackpack,[switch]$AppearanceOnly)
$ErrorActionPreference='Stop'
$tacticalProject='D:/FPS3D/FPSGAME'
$tacticalTools=Join-Path $tacticalProject 'Tools/ModernTacticalSet'
$tacticalRoot=Join-Path $tacticalProject 'SourceAssets/ModernTacticalSet20261113/Integration'
function Invoke-TacticalStage([string]$script){
    & (Join-Path $tacticalTools 'run_asset.ps1') -Script ($script+'.py') -ReceiptName ($script+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    if($LASTEXITCODE -ne 0){throw "Asset stage stopped: $script"}
}
if(-not $ResumeBackpack){
    if(-not $ResumeAssets){
        & python (Join-Path $tacticalTools 'derive.py') *> (Join-Path $tacticalRoot 'Logs/derive.log')
        if($LASTEXITCODE -ne 0){throw 'Native garment authoring stopped'}
        & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --factory-startup -b -t 6 --python-exit-code 1 --python (Join-Path $tacticalTools 'fit_vest_contact.py') *> (Join-Path $tacticalRoot 'Logs/female-clearance.log')
        if($LASTEXITCODE -ne 0){throw 'Female carrier contact authoring stopped'}
        & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --factory-startup -b -t 6 --python-exit-code 1 --python (Join-Path $tacticalTools 'export_glove_parts.py') *> (Join-Path $tacticalRoot 'Logs/glove-parts.log')
        if($LASTEXITCODE -ne 0){throw 'Native glove component export stopped'}
        & python (Join-Path $tacticalTools 'fit_first_person.py') *> (Join-Path $tacticalRoot 'Logs/fp-fit.log')
        if($LASTEXITCODE -ne 0){throw 'V7 glove production stopped'}
    }
    do{
        Invoke-TacticalStage 'save_assets'
        $tacticalGarments=Get-Content -LiteralPath (Join-Path $tacticalRoot 'saved_assets.json') -Raw | ConvertFrom-Json
    }while(-not $tacticalGarments.completed)
    & python (Join-Path $tacticalTools 'publish_body_only.py')
    if($LASTEXITCODE -ne 0){throw 'Vest viewmodel policy publication stopped'}
    $tacticalPublishArgs=@()
    if($AppearanceOnly){$tacticalPublishArgs+=('--appearance-only')}
    & python (Join-Path $tacticalTools 'publish.py') @tacticalPublishArgs
    if($LASTEXITCODE -ne 0){throw 'Scoped equipment publication stopped'}
}
$env:BACKPACK_FIT_RUN_DIR=Join-Path $tacticalProject 'SourceAssets/BackpackFit20261024/ModernTacticalFitR320261114'
$env:BACKPACK_FIT_SHIRT='ue_modern_kevlar_vest'
$tacticalPack=Join-Path $tacticalProject 'Tools/BackpackFit'
if(-not(Test-Path (Join-Path $env:BACKPACK_FIT_RUN_DIR 'authored.json'))){
    & python (Join-Path $tacticalPack 'pending.py')
    if($LASTEXITCODE -ne 0){throw 'Backpack preparation stopped'}
    Invoke-TacticalStage 'backpack_capture'
    & python (Join-Path $tacticalPack 'classify_cargo.py')
    if($LASTEXITCODE -ne 0){throw 'Backpack strap separation stopped'}
    foreach($tacticalScript in @('surfaces','sample_shells')){
        & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --factory-startup -b -t 6 --python-exit-code 1 --python (Join-Path $tacticalPack ($tacticalScript+'.py')) *> (Join-Path $env:BACKPACK_FIT_RUN_DIR ($tacticalScript+'.log'))
        if($LASTEXITCODE -ne 0){throw "Backpack surface production stopped: $tacticalScript"}
    }
    & python (Join-Path $tacticalPack 'author_contact.py') *> (Join-Path $env:BACKPACK_FIT_RUN_DIR 'author.log')
    if($LASTEXITCODE -ne 0){throw 'Backpack contact authoring stopped'}
}
do{
    Invoke-TacticalStage 'backpack_save'
    $tacticalSaved=Get-Content -LiteralPath (Join-Path $env:BACKPACK_FIT_RUN_DIR 'saved_assets.json') -Raw | ConvertFrom-Json
}while(-not $tacticalSaved.completed)
foreach($tacticalScript in @('publish','register')){
    & python (Join-Path $tacticalPack ($tacticalScript+'.py'))
    if($LASTEXITCODE -ne 0){throw "Backpack integration stopped: $tacticalScript"}
}
if(-not $AppearanceOnly){
    & (Join-Path $tacticalTools 'grant_inventory.ps1')
    if($LASTEXITCODE -ne 0){throw 'Inventory grant stopped; retain original profile'}
}
if($AppearanceOnly){
    Write-Output 'TS01 appearance, inventory artwork and backpack combinations saved. Existing item IDs retained. No gameplay tests run.'
}else{
    Write-Output 'TS01 equipment, inventory artwork, backpack combinations and saved inventory delivered. No gameplay tests run.'
}
