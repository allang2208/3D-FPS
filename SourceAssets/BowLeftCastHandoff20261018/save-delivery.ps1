$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets/BowLeftCastHandoff20261018'
$paths=@(
    'Source/FPSGAME/Weapons/Bow/BowCastHandPose.h',
    'Source/FPSGAME/Weapons/Bow/BowArmsMeshComponent.h',
    'Source/FPSGAME/Weapons/Bow/BowArmsMeshComponent.cpp',
    'Source/FPSGAME/Weapons/Bow/BowWeaponComponent.h',
    'Source/FPSGAME/Weapons/Bow/BowWeaponComponent.cpp',
    'Source/FPSGAME/Skills/FPSCastingMeshComponent.h',
    'Source/FPSGAME/Skills/FPSFireballComponent.h',
    'Source/FPSGAME/Skills/FPSFireballComponent.cpp',
    'Source/FPSGAME/Characters/FPSBodyBowMotion.h',
    'Source/FPSGAME/Characters/FPSBodyBowPose.inl',
    'Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyActions.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyTypes.h',
    'Source/FPSGAME/Characters/FPSPlayerBodyNetwork.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyBow.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyMotion.cpp',
    'Source/FPSGAME/Characters/BowSparrowPresentationAudit.cpp',
    'Docs/Characters/bow-left-cast-handoff-20261018.md'
)
$sources=@(foreach($relative in $paths){
    $full=Join-Path $projectRoot $relative
    [ordered]@{path=$relative;sha256=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash;last_write_utc=(Get-Item -LiteralPath $full).LastWriteTimeUtc.ToString('o')}
})
$builds=@(Get-ChildItem -LiteralPath $taskRoot -Directory -Filter 'Build-*' | Sort-Object Name | ForEach-Object {
    $receipt=Join-Path $_.FullName 'result.json'
    if(Test-Path -LiteralPath $receipt){[ordered]@{receipt=$receipt;result=(Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json)}}
})
$builds=@($builds | Group-Object { $_.result.target } | ForEach-Object { $_.Group[-1] })
[ordered]@{
    task='Bow left-hand casting with persistent right-hand support'
    saved_at=(Get-Date).ToString('o')
    source_saved=$true
    sources=$sources
    builds=$builds
    assets_reauthored=$false
    editor_launched=$false
    runtime_tests_run=$false
    automation_tests_run=$false
    visual_acceptance='Pending user in-game review'
    multiplayer_acceptance='Presentation fields integrated; no real host-client test run'
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskRoot 'delivery.json') -Encoding UTF8
Write-Output (Join-Path $taskRoot 'delivery.json')
