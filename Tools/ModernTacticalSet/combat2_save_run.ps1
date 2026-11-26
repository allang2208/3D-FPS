$ErrorActionPreference='Stop'
$combatTools='D:/FPS3D/FPSGAME/Tools/ModernTacticalSet'
$combatRoot='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR2'
$combatBlender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
function Require-CombatStep($name){if($LASTEXITCODE -ne 0){throw "Stopped: $name"}}
& $combatBlender --factory-startup -b -t 6 --python-exit-code 1 --python "$combatTools/combat2_calf_fit.py" *> "$combatRoot/Logs/calf-fit.log"
Require-CombatStep 'calf fit'
& $combatBlender --factory-startup -b -t 6 --python-exit-code 1 --python "$combatTools/combat2_assemble.py" *> "$combatRoot/Logs/assemble.log"
Require-CombatStep 'world and owner assemblies'
Remove-Item Env:TS01_SHIRT_SAVE_PLAN -ErrorAction SilentlyContinue
$combatStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
for($combatBatch=0;$combatBatch -lt 12;$combatBatch++){
    & "$combatTools/run_asset.ps1" -Script combat2_save.py -ReceiptName "combat2-wear-$combatStamp-$combatBatch"
    Require-CombatStep 'wearable save'
    $combatSaved=Get-Content -LiteralPath "$combatRoot/saved.json" -Raw | ConvertFrom-Json
    if($combatSaved.completed){break}
}
if(-not $combatSaved.completed){throw 'Wearable asset saves remain incomplete'}
while((-not(Test-Path -LiteralPath "$combatRoot/artwork.json")) -or (-not(Test-Path -LiteralPath "$combatRoot/lower-artwork.json"))){Start-Sleep -Seconds 5}
& "$combatTools/run_asset.ps1" -Script combat2_save_artwork.py -ReceiptName "combat2-artwork-$combatStamp"
Require-CombatStep 'artwork save'
Write-Output 'TS01_COMBAT2_ASSETS_READY_FOR_RELEASE'
