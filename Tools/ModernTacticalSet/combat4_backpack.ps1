param([switch]$ResumeSave)
$ErrorActionPreference='Stop'
$r4Project='D:/FPS3D/FPSGAME'
$r4Root="$r4Project/SourceAssets/ModernTacticalSet20261113/CombatShirtR4"
$r4Fit="$r4Project/SourceAssets/BackpackFit20261024/ModernTacticalShirtR420261115"
$env:BACKPACK_FIT_RUN_DIR=$r4Fit
$env:BACKPACK_FIT_SHIRT='ue_modern_kevlar_vest'
$env:BACKPACK_FIT_NEW_ASSETS_ONLY='1'
$r4Call="$r4Project/Tools/ModernTacticalSet/combat4_stage_call.ps1"
if(-not $ResumeSave) {
    & python -X utf8 "$r4Project/Tools/BackpackFit/pending.py"
    if($LASTEXITCODE -ne 0){throw 'Backpack input preparation stopped'}
    $r4Pending=Get-Content -LiteralPath "$r4Fit/pending.json" -Raw | ConvertFrom-Json
    if($r4Pending.count -eq 0){Write-Output 'R4 backpack pairs are current';exit 0}
    & $r4Call -Script "$r4Project/Tools/BackpackFit/capture.py" -Label 'backpack-capture'
    if($LASTEXITCODE -ne 0){throw 'Backpack source capture stopped'}
    & python -X utf8 "$r4Project/Tools/BackpackFit/classify_cargo.py"
    if($LASTEXITCODE -ne 0){throw 'Backpack cargo classification stopped'}
    foreach($r4Step in @('surfaces','sample_shells')) {
        & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --factory-startup -b -t 6 --python-exit-code 1 --python "$r4Project/Tools/BackpackFit/$r4Step.py" *> "$r4Fit/$r4Step.log"
        if($LASTEXITCODE -ne 0){throw "Backpack contact preparation stopped: $r4Step"}
    }
    & python -X utf8 "$r4Project/Tools/BackpackFit/author_contact.py" *> "$r4Fit/author.log"
    if($LASTEXITCODE -ne 0){throw 'Backpack authoring stopped'}
}
for($r4Batch=0;$r4Batch -lt 5;$r4Batch++) {
    & $r4Call -Script "$r4Project/Tools/BackpackFit/save_assets.py" -Label "backpack-save-$r4Batch"
    if($LASTEXITCODE -ne 0){throw 'Backpack save stopped; retain revision and resume'}
    $r4Saved=Get-Content -LiteralPath "$r4Fit/saved_assets.json" -Raw | ConvertFrom-Json
    if($r4Saved.completed){break}
}
if(-not $r4Saved.completed){throw 'Backpack assets remain incomplete'}
& python -X utf8 "$r4Project/Tools/BackpackFit/publish.py"
if($LASTEXITCODE -ne 0){throw 'Backpack config publication stopped'}
& python -X utf8 "$r4Project/Tools/BackpackFit/register.py"
if($LASTEXITCODE -ne 0){throw 'Backpack dependency registration stopped'}
Write-Output 'R4_SEVEN_BACKPACKS_BOTH_BODIES_SAVED_AND_INTEGRATED'
