$ErrorActionPreference='Stop'
$quickBuildReceipt=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Raw | ConvertFrom-Json
$quickAfterReceipt=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'after-cached-ash12-receipt.json') -Raw | ConvertFrom-Json
$quickBeforeResult=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'before-cached-ash12-trace.txt') -Tail 1
$quickAfterResult=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'after-cached-ash12-trace.txt') -Tail 1
$quickDelivery=[ordered]@{
    revision='QuickCombatOwnershipFixV4_20261015'
    recorded=(Get-Date).ToString('s')
    source_saved=$true
    changes=@('ASH weapon-state cancellation and advancement restricted to rifle quick-combat styles','Hammer head probe uses native WPN_root units without a second 100x conversion')
    source_files=@('Source/FPSGAME/FPSGAMECharacter.cpp','Source/FPSGAME/Production/WarhammerQuickCombatMarker.h','SourceAssets/SteelWarhammer20261014/QuickCombatHeadThrustV3/author_head_thrust.py','SourceAssets/SteelWarhammer20261014/QuickCombatHeadThrustV3/authored.json','Source/FPSGAME/Production/WarhammerSprintAuditCommandlet.cpp')
    prerequisite_compile_repairs=@('Source/FPSGAME/Building/CampfireCookingPresentation.cpp','Source/FPSGAME/Skills/DragonBreathEntryAuditDiagnostics.cpp')
    builds=$quickBuildReceipt
    targeted_reproduction=[ordered]@{before=$quickBeforeResult;after=$quickAfterResult;after_exit_code=$quickAfterReceipt.exit_code}
    user_equipment_diagnosis='not_run: existing commandlet followed by a newly opened editor; preserved editor state'
    animation=[ordered]@{path='/Game/Weapons/SteelWarhammer20261014/QuickCombatV1/A_Warhammer_QuickCombat';source_revision='HeadThrustV3_20261015';changed_this_fix=$false;total_seconds=0.5;contact_seconds=0.15}
    user_save_modified=$false
    game_launched=$false
    visual_acceptance='pending_user'
    multiplayer_acceptance='not_performed'
    evidence_limit='The original user F press was not captured completely; the cached ASH scenario reproduces the symptom and passes after the fix.'
}
$quickDelivery | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'delivery.json') -Encoding utf8
Write-Output ('Saved '+(Join-Path $PSScriptRoot 'delivery.json'))
