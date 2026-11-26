param([switch]$ResumeBackpack)
$ErrorActionPreference='Stop'
$combatProject='D:/FPS3D/FPSGAME'
$combatTools="$combatProject/Tools/ModernTacticalSet"
$combatRoot="$combatProject/SourceAssets/ModernTacticalSet20261113/CombatShirtR1"
if(Test-Path -LiteralPath "$combatRoot/release-block.json"){throw 'This draft is superseded by the user-requested concept-fidelity rebuild.'}
$combatBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$combatStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
function Assert-CombatStep($name){if($LASTEXITCODE -ne 0){throw "Combat production stopped: $name"}}
if(-not $ResumeBackpack){
    while(-not(Test-Path -LiteralPath "$combatRoot/authored.json")){Start-Sleep -Seconds 5}
    Remove-Item Env:TS01_SHIRT_SAVE_PLAN -ErrorAction SilentlyContinue
    & "$combatTools/run_asset.ps1" -Script shirt_save.py -ReceiptName "combat-wear-$combatStamp"
    Assert-CombatStep 'save wearable meshes'
    & python -X utf8 "$combatTools/shirt_display_fix.py"
    Assert-CombatStep 'display native cloth shoulders'
    & $combatBlender --factory-startup -b -t 6 --python-exit-code 1 --python "$combatTools/shirt_sources.py" *> "$combatRoot/Logs/sources-final.log"
    Assert-CombatStep 'editable sources and inventory icon'
    & "$combatTools/run_asset.ps1" -Script shirt_save_artwork.py -ReceiptName "combat-artwork-$combatStamp"
    Assert-CombatStep 'save display and pickup'
    & python -X utf8 "$combatTools/shirt_publish.py"
    Assert-CombatStep 'publish garment routes'
}
$env:BACKPACK_FIT_RUN_DIR="$combatProject/SourceAssets/BackpackFit20261024/ModernTacticalShirtR120261114"
$env:BACKPACK_FIT_SHIRT='ue_modern_kevlar_vest'
if(-not(Test-Path -LiteralPath "$env:BACKPACK_FIT_RUN_DIR/authored.json")){
    & python -X utf8 "$combatProject/Tools/BackpackFit/pending.py"
    Assert-CombatStep 'prepare backpack combinations'
    & "$combatTools/run_asset.ps1" -Script combat_backpack_capture.py -ReceiptName "combat-backpack-capture-$combatStamp"
    Assert-CombatStep 'capture backpack combinations'
    & python -X utf8 "$combatProject/Tools/BackpackFit/classify_cargo.py"
    Assert-CombatStep 'classify backpack cargo'
    foreach($combatScript in @('surfaces','sample_shells')){
        & $combatBlender --factory-startup -b -t 6 --python-exit-code 1 --python "$combatProject/Tools/BackpackFit/$combatScript.py" *> "$env:BACKPACK_FIT_RUN_DIR/$combatScript.log"
        Assert-CombatStep $combatScript
    }
    & python -X utf8 "$combatProject/Tools/BackpackFit/author_contact.py" *> "$env:BACKPACK_FIT_RUN_DIR/author.log"
    Assert-CombatStep 'author backpack contact'
}
for($combatBatch=0;$combatBatch -lt 5;$combatBatch++){
    & "$combatTools/run_asset.ps1" -Script combat_backpack_save.py -ReceiptName "combat-backpack-save-$combatStamp-$combatBatch"
    Assert-CombatStep 'save backpack fit'
    $combatSaved=Get-Content -LiteralPath "$env:BACKPACK_FIT_RUN_DIR/saved_assets.json" -Raw | ConvertFrom-Json
    if($combatSaved.completed){break}
}
if(-not $combatSaved.completed){throw 'Backpack asset batch incomplete'}
& python -X utf8 "$combatProject/Tools/BackpackFit/publish.py"
Assert-CombatStep 'publish backpack fit'
& python -X utf8 "$combatProject/Tools/BackpackFit/register.py"
Assert-CombatStep 'record backpack dependency'
Write-Output 'TS01_COMBAT_DELIVERY_COMPLETE'
