param([switch]$ResumeSave)
$ErrorActionPreference='Stop'
$cuffTools='D:/FPS3D/FPSGAME/Tools/ModernTacticalSet'
$cuffRoot='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3'
function Require-CuffStep($name){if($LASTEXITCODE -ne 0){throw "Stopped: $name"}}
if(-not $ResumeSave){
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --factory-startup -b -t 1 --python-exit-code 1 --python "$cuffTools/combat3_cuff_native_glove.py" *> "$cuffRoot/CuffRepairR1/Logs/native-cuff-finalize.log"
Require-CuffStep 'finalize native glove cuffs'
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --factory-startup -b -t 1 --python-exit-code 1 --python "$cuffTools/combat3_cuff_body_clearance.py" *> "$cuffRoot/CuffRepairR1/Logs/body-cuff-finalize.log"
Require-CuffStep 'finalize Body cuff clearance'
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --factory-startup -b -t 1 --python-exit-code 1 --python "$cuffTools/combat3_cuff_finish_binding.py" *> "$cuffRoot/CuffRepairR1/Logs/sleeve-binding-finalize.log"
Require-CuffStep 'finalize sleeve-only bone weights'
& python -X utf8 "$cuffTools/combat3_cuff_collect.py"
Require-CuffStep 'collect native glove wrist sources'
& python -X utf8 "$cuffTools/combat3_cuff_promote.py"
Require-CuffStep 'promote authored cuff sources'
}
foreach($cuffPlan in @('combat3_save_final.py','combat3_cuff_save_gloves.py')){
    for($cuffBatch=0;$cuffBatch -lt 12;$cuffBatch++){
        & "$cuffTools/run_asset.ps1" -Script $cuffPlan -ReceiptName ('cuff-save-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
        Require-CuffStep 'save cuff asset batch'
        $cuffSaved=Get-Content -LiteralPath "$cuffRoot/saved.json" -Raw | ConvertFrom-Json
        if($cuffSaved.completed){break}
    }
    if(-not $cuffSaved.completed){throw 'Cuff asset plan remains incomplete'}
}
& "$cuffTools/run_asset.ps1" -Script combat3_save_artwork.py -ReceiptName ('cuff-art-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
Require-CuffStep 'save revised inventory artwork'
& python -X utf8 "$cuffTools/combat3_publish.py"
Require-CuffStep 'publish current garment fields'
& python -X utf8 "$cuffTools/combat3_cuff_publish_gloves.py"
Require-CuffStep 'publish wrist glove fields'
& python -X utf8 "$cuffTools/combat3_cuff_publish.py"
Require-CuffStep 'record saved cuff revision'
& "$cuffTools/combat3_backpack_run.ps1"
Require-CuffStep 'save paired backpacks'
& python -X utf8 "$cuffTools/combat3_delivery.py"
exit $LASTEXITCODE
