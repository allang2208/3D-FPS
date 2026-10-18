$ErrorActionPreference='Stop'
$reviewRoot='D:/FPS3D/FPSGAME'
$owned=@('Source/FPSGAME/Items/FPSPotionUseComponent.h','Source/FPSGAME/Items/FPSPotionUseComponent.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyBow.cpp','Source/FPSGAME/Characters/FPSBodyBowMotion.h','Source/FPSGAME/Characters/FPSPlayerBodyMotion.cpp',
    'Source/FPSGAME/Weapons/Bow/BowWeaponComponent.cpp','Source/FPSGAME/FPSGAMEConsumableUse.cpp','Source/FPSGAME/FPSGAMECharacter.cpp',
    'Source/FPSGAME/Characters/BowSparrowPresentationAudit.cpp','Source/FPSGAME/Weapons/Bow/BowSparrowWireAudit.cpp','Content/ColdSteelData/melee-gunsmith.json')
$builds=@()
foreach($target in @('Game','Editor')){
    $receipt=Get-ChildItem -LiteralPath $PSScriptRoot -Directory | Where-Object {$_.Name -like "Build-*-$target"} | Sort-Object Name -Descending | Select-Object -First 1
    if(-not $receipt -or -not (Test-Path -LiteralPath "$($receipt.FullName)/result.json")){throw "Latest $target build did not succeed"}
    $builds+=Get-Content -LiteralPath "$($receipt.FullName)/result.json" -Raw | ConvertFrom-Json
}
$isolated=Get-Content -LiteralPath "$PSScriptRoot/isolated-receipt.json" -Raw | ConvertFrom-Json
$cases=Get-Content -LiteralPath "$($isolated.directory)/result.json" -Raw | ConvertFrom-Json
$wire=Get-Content -LiteralPath "$PSScriptRoot/wire-receipt.json" -Raw | ConvertFrom-Json
$netCases=Get-Content -LiteralPath "$($wire.directory)/host.json" -Raw | ConvertFrom-Json
if($isolated.exit_code -ne 0 -or $cases.failed -ne 0 -or -not $wire.passed){throw 'Review did not pass completely'}
@{
    saved_at=(Get-Date -Format o)
    scope='Bow shared left-hand casting and consumption presentation, normal and interrupted recovery'
    source=@($owned | ForEach-Object {@{path=$_;sha256=(Get-FileHash -LiteralPath "$reviewRoot/$_" -Algorithm SHA256).Hash}})
    builds=$builds
    isolated=@{receipt=$isolated;cases=$cases.cases;failed=$cases.failed}
    socket_transport=$wire
    socket_cases=$netCases
    visual_acceptance=$false
    full_economy_end_to_end=$false
    normal_player_profile_used=$false
    binary_assets_modified=$false
} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$PSScriptRoot/delivery.json" -Encoding utf8
Write-Output "BOW_HANDOFF_DELIVERY $PSScriptRoot/delivery.json"
