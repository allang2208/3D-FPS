param([switch]$ResumeSave)
$ErrorActionPreference='Stop'
$combatProject='D:/FPS3D/FPSGAME'
$combatTools="$combatProject/Tools/ModernTacticalSet"
$combatFit="$combatProject/SourceAssets/BackpackFit20261024/ModernTacticalShirtR220261114"
$combatBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$env:BACKPACK_FIT_RUN_DIR=$combatFit
$env:BACKPACK_FIT_SHIRT='ue_modern_kevlar_vest'
function Require-CombatFitStep($name){if($LASTEXITCODE -ne 0){throw "Stopped: $name"}}
if(-not $ResumeSave){
    & python -X utf8 "$combatProject/Tools/BackpackFit/pending.py"
    Require-CombatFitStep 'backpack input plan'
    $combatPending=Get-Content -LiteralPath "$combatFit/pending.json" -Raw | ConvertFrom-Json
    if($combatPending.count -eq 0){Write-Output 'Current clothing pairs already saved.';exit 0}
    for($combatCaptureBatch=0;$combatCaptureBatch -lt 20;$combatCaptureBatch++){
        & "$combatTools/run_asset.ps1" -Script combat2_backpack_capture.py -ReceiptName ('combat2-pack-capture-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
        Require-CombatFitStep 'backpack native capture'
        $combatCapture=Get-Content -LiteralPath "$combatFit/capture_status.json" -Raw | ConvertFrom-Json
        if($combatCapture.state -eq 'completed'){break}
    }
    if($combatCapture.state -ne 'completed'){throw 'Native backpack surfaces remain incomplete'}
    & python -X utf8 "$combatProject/Tools/BackpackFit/classify_cargo.py"
    Require-CombatFitStep 'cargo separation'
    foreach($combatStage in @('surfaces','sample_shells')){
        & $combatBlender --factory-startup -b -t 6 --python-exit-code 1 --python "$combatProject/Tools/BackpackFit/$combatStage.py" *> "$combatFit/$combatStage.log"
        Require-CombatFitStep $combatStage
    }
    & python -X utf8 "$combatProject/Tools/BackpackFit/author_contact.py" *> "$combatFit/author.log"
    Require-CombatFitStep 'backpack contact production'
}
$combatAuthored=Get-Content -LiteralPath "$combatFit/authored.json" -Raw | ConvertFrom-Json
for($combatBatch=0;$combatBatch -le [Math]::Ceiling(($combatAuthored.rows.Count+$combatAuthored.statics.Count)/24);$combatBatch++){
    & "$combatTools/run_asset.ps1" -Script combat2_backpack_save.py -ReceiptName ('combat2-pack-save-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    Require-CombatFitStep 'backpack asset save'
    $combatSaved=Get-Content -LiteralPath "$combatFit/saved_assets.json" -Raw | ConvertFrom-Json
    if($combatSaved.completed){break}
}
if(-not $combatSaved.completed){throw 'Backpack saved assets remain incomplete'}
& python -X utf8 "$combatProject/Tools/BackpackFit/publish.py"
Require-CombatFitStep 'backpack field publication'
& python -X utf8 "$combatProject/Tools/BackpackFit/register.py"
Require-CombatFitStep 'backpack dependency registration'
Write-Output 'TS01_COMBAT2_BACKPACKS_SAVED_AND_INTEGRATED'
