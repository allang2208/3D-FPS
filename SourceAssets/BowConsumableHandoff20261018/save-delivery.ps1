$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets/BowConsumableHandoff20261018'
$paths=@(
    'Source/FPSGAME/FPSGAMEConsumableUse.cpp',
    'Source/FPSGAME/Items/FPSPotionUseComponent.h',
    'Source/FPSGAME/Items/FPSPotionUseComponent.cpp',
    'Source/FPSGAME/Weapons/Bow/BowWeaponComponent.h',
    'Source/FPSGAME/Weapons/Bow/BowWeaponComponent.cpp',
    'Source/FPSGAME/Weapons/Bow/BowArmsMeshComponent.h',
    'Source/FPSGAME/Weapons/Bow/BowArmsMeshComponent.cpp',
    'Source/FPSGAME/Characters/FPSBodyBowMotion.h',
    'Source/FPSGAME/Characters/FPSBodyBowPose.inl',
    'Source/FPSGAME/Characters/FPSPlayerBodyTypes.h',
    'Source/FPSGAME/Characters/FPSPlayerBodyNetwork.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyBow.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp',
    'Source/FPSGAME/Characters/BowSparrowPresentationAudit.cpp',
    'Source/FPSGAME/Items/FPSConsumableAuditCommandlet.cpp',
    'Source/FPSGAME/Development/NonHumanoidHitAuditCommandlet.cpp',
    'Docs/Characters/bow-consumable-handoff-20261018.md'
)
$sources=@(foreach($relative in $paths){
    [ordered]@{path=$relative;sha256=(Get-FileHash -LiteralPath (Join-Path $projectRoot $relative) -Algorithm SHA256).Hash}
})
$builds=@(Get-ChildItem -LiteralPath $taskRoot -Directory -Filter 'Build-*' | Sort-Object Name | ForEach-Object {
    $receipt=Join-Path $_.FullName 'result.json'
    if(Test-Path -LiteralPath $receipt){[ordered]@{receipt=$receipt;result=(Get-Content -LiteralPath $receipt -Raw|ConvertFrom-Json)}}
})
$builds=@($builds|Group-Object {$_.result.target}|ForEach-Object {$_.Group[-1]})
[ordered]@{
    task='Bow consumable support, third-person stow and hand recovery'
    saved_at=(Get-Date).ToString('o')
    source_saved=$true
    sources=$sources
    builds=$builds
    assets_reauthored=$false
    editor_launched=$false
    runtime_tests_run=$false
    automation_tests_run=$false
    review_scope='Targeted source routing and presentation review; no visual or host-client acceptance'
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskRoot 'delivery.json') -Encoding UTF8
Write-Output (Join-Path $taskRoot 'delivery.json')
