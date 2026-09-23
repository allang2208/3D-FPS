<#
Static weapon rain-wetness coverage audit (no editor required).

Why this exists
---------------
Weapon rain wetness is not driven by the weather MPC. UWeatherViewEffectsComponent
swaps a per-slot material on every mesh attached to the pawn's `AKMViewmodel`
component, looking the dry material's object path up in
UWeatherPresentationAssets::WetMaterials. A weapon or attachment slot that has no
entry in that map simply never gets wet, and nothing warns about it.

Runtime-effective table = /Game/Weather/RainVisibility/DA_WeatherPresentation
  merged with the tables that WeatherViewEffectsComponent::Initialize adds:
    DanWesson715WeaponAssets::WetMaterialsPath
    ASH12WeaponAssets::WetMaterialsPath
    PKMLowpolyWeaponAssets::WetMaterialsPath
    /Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials
  plus the three ExtMagContinuity20260919 dry/wet pairs.

Usage
-----
  pwsh -File Tools/Weather/audit_weapon_wetness.ps1            # grouped report
  pwsh -File Tools/Weather/audit_weapon_wetness.ps1 -OnlyDry  # uncovered only

This is a read-only static check. It reports what the built content contains; it
does not load the game and does not prove on-screen appearance.
#>
[CmdletBinding()]
param(
    [switch]$OnlyDry,
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
$Content = Join-Path $ProjectRoot 'Content'
$Latin1 = [System.Text.Encoding]::GetEncoding(28591)

# Runtime wetness tables actually merged by UWeatherViewEffectsComponent::Initialize.
$RuntimeTables = @(
    'Weather\RainVisibility\DA_WeatherPresentation.uasset',
    'Weapons\DanWesson715\AccessoryPolymer20260914\DA_DW715_WetMaterials.uasset',
    'Weapons\ASH12\Surface20260919\DA_ASH12_WetMaterials.uasset',
    'Weapons\PKMLowpoly20260922\Finish20\DA_PKM_WetMaterials.uasset',
    'Weapons\M16A2\UniversalAttachments20260920\DA_M16_AttachmentWetMaterials.uasset'
)

# Weapon/attachment content that the shipped resolvers can actually mount.
# Sources: FPSGAMECharacter.cpp weapon table, M4GunsmithVisual/M4MuzzleVisual/
# M4*Foregrip/M4HandstopVisual/M4DrumVisual, AKMAttachmentVisual.h,
# ASH12Attachments.h, M16Attachments.h, PKMAttachments.h, QBZ191Attachments.h,
# A762Attachments.h, SkeletonStockVisual.cpp, PhantomRearGripVisual.cpp,
# TacticalDeviceComponent.cpp, DanWesson715WeaponAssets.h, M1911WeaponAssets.h.
$RuntimeDirs = @(
    'Weapons\M4HK416Replica',
    'Weapons\AKMIntegration\SovietFab',
    'Weapons\QBZ191\RearGrip20260913',
    'Weapons\QBZ191\Attachments20260913',
    'Weapons\ASH12\Surface20260919',
    'Weapons\ASH12\UniversalAttachments20260919',
    'Weapons\ASH12\TacticalSuppressor20260919',
    'Weapons\ASH12\CheekRest20260919',
    'Weapons\M16A2\Gameplay20260919',
    'Weapons\M16A2\UniversalAttachments20260920',
    'Weapons\M1911\RearFinish20260913',
    'Weapons\M1911\CompactFit20260913',
    'Weapons\M1911\SculptedMount20260913',
    'Weapons\M1911\MuzzleRedDot20260913',
    'Weapons\M1911\Tactical20260913',
    'Weapons\DanWesson715\Chrome20260914',
    'Weapons\DanWesson715\AccessoryPolymer20260914',
    'Weapons\A762\Integrated20260920',
    'Weapons\A762\Accessories05',
    'Weapons\SVDDragunov20260922',
    'Weapons\PKMLowpoly20260922\Accessories14',
    'Weapons\AttachmentFinish20260913',
    'Weapons\M4MuzzlesV1',
    'Weapons\M4VerticalGripCompact75',
    'Weapons\M4CantedForegrip',
    'Weapons\M4AngledForegripCompact75',
    'Weapons\M4Drum',
    'Weapons\M4Holographic',
    'Weapons\LPVO1to6X',
    'Weapons\PanoramicRedDot',
    'Weapons\PrismHandstopV1',
    'Weapons\PrismScope2XMachined',
    'Weapons\M4GridUnified20260919',
    'Weapons\ExtMagContinuity20260919',
    'Weapons\MagazineMouthFinish20260919',
    'Weapons\TacticalSuppressor20260913',
    'Weapons\TacticalDevices20260913',
    'Weapons\CoreStock20260914',
    'Weapons\QRPerformanceStock',
    'Weapons\ReferenceStock5080',
    'Weapons\TacticalTelescopicStock20260914',
    'Weapons\PhantomRearGrip',
    'Weapons\StableAntiSlipRearGrip',
    'Weapons\RearGripFinish20260913',
    'Weapons\ResonanceGrip20260913'
)

# Superseded sibling folders that live under a runtime directory but that no
# resolver loads any more. Without this list the report drowns in legacy copies.
$SkipPaths = @(
    'CoreStock20260914/(AKM|M4|QBZ191)/',              # runtime: Meshy0914005605/
    'QRPerformanceStock/(AKM|M4)/',                    # runtime: Meshy20260913/
    'ReferenceStock5080/(Refined/AKM|Refined/M4|Refined91379/)',
    'ResonanceGrip20260913/(AKM|M4|Repaired91871|SurfaceRefine|QBZ191)/',  # runtime: MeshyIntegration/
    'TacticalDevices20260913/HunyuanV3/',              # runtime: TacticalDevices20260913/<family>/
    'PhantomRearGrip/(AKM|M4|QBZ191)/',                # runtime: RearGripFinish20260913/<family>/phantom/
    'StableAntiSlipRearGrip/(AKM|M4|QBZ191)/',         # runtime: StableAntiSlipRearGrip/Selected91727/
    'AKMIntegration/SovietFab/Attachments/SM_AKM_(angled|optic|prism)',  # runtime: ResonanceGrip / OpticSteel / AttachmentFinish
    'SVDDragunov20260922/(Meshes|Viewmodel)/'          # runtime: Complete20260923/
) -join '|'

# Slots that are dry on purpose, per ue5-weapon-workflow/references/weapon-finish.md:
# shared Manny arms/hands, optic glass and reticles, and muzzle cavities stay non-wet.
$IntentionalDry = 'MI_Manny|Reticle|Glass|Lens|_Inner|MuzzleRecess|Suppressor_Recess'

function Get-Strings([string]$Path, [int]$Min = 6) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $set = New-Object System.Collections.Generic.HashSet[string]
    foreach ($m in [regex]::Matches($Latin1.GetString($bytes), '[\x20-\x7E]{' + $Min + ',}')) { [void]$set.Add($m.Value) }
    return $set
}

function Get-GameFile([string]$GamePath) {
    Join-Path $Content (($GamePath -replace '^/Game/', '') -replace '/', '\')
}

# Classify by exact class-name tokens in the asset name map: a StaticMesh that
# imports material instances also contains "MaterialInstanceConstant", so mesh
# class tokens must win.
function Get-AssetKind([string]$File) {
    if (-not (Test-Path $File)) { return 'Missing' }
    $s = Get-Strings $File 4
    if ($s.Contains('SkeletalMesh')) { return 'SkeletalMesh' }
    if ($s.Contains('StaticMesh')) { return 'StaticMesh' }
    if ($s.Contains('MaterialInstanceConstant')) { return 'MaterialInstanceConstant' }
    foreach ($x in $s) { if ($x.StartsWith('MaterialExpression')) { return 'Material' } }
    if ($s.Contains('Material')) { return 'Material' }
    return 'Other'
}

Write-Host "Weapon rain-wetness coverage audit"
Write-Host "  project: $ProjectRoot"

$wetKeys = New-Object System.Collections.Generic.HashSet[string]
foreach ($t in $RuntimeTables) {
    $p = Join-Path $Content $t
    if (-not (Test-Path $p)) { Write-Warning "missing wetness table: $t"; continue }
    foreach ($s in (Get-Strings $p 8)) {
        if ($s -match '^/Game/.+/\w+\.\w+$') { [void]$wetKeys.Add($s) }
    }
}
Write-Host ("  runtime wet-table keys: {0}" -f $wetKeys.Count)

$rows = New-Object System.Collections.Generic.List[object]
foreach ($dir in $RuntimeDirs) {
    $full = Join-Path $Content $dir
    if (-not (Test-Path $full)) { Write-Warning "missing runtime dir: $dir"; continue }
    foreach ($a in Get-ChildItem $full -Recurse -Include *.uasset -File) {
        $rel = $a.FullName.Substring($Content.Length).Replace('\', '/')
        if ($rel -match '/(Before|Candidates)/') { continue }
        if ($rel -match $SkipPaths) { continue }
        if ($a.Name -notmatch '^(SM_|SK_)') { continue }
        $mesh = '/Game' + ($rel -replace '\.uasset$', '')
        $kind = Get-AssetKind $a.FullName
        if ($kind -notin @('StaticMesh', 'SkeletalMesh')) { continue }

        $refs = New-Object System.Collections.Generic.HashSet[string]
        foreach ($s in (Get-Strings $a.FullName 8)) {
            if ($s -match '^/Game/[\w/]+$' -and $s -ne $mesh) { [void]$refs.Add($s) }
        }
        foreach ($r in ($refs | Sort-Object)) {
            $rk = Get-AssetKind ((Get-GameFile $r) + '.uasset')
            if ($rk -notin @('Material', 'MaterialInstanceConstant')) { continue }
            $dry = "$r.$([System.IO.Path]::GetFileName($r))"
            if ($wetKeys.Contains($dry)) { $state = 'WET' }
            elseif ($dry -match $IntentionalDry) { $state = 'INTENTIONAL' }
            else { $state = 'DRY' }
            $rows.Add([pscustomobject]@{ Mesh = $mesh; Material = $dry; State = $state })
        }
    }
}

$considered = $rows | Where-Object { $_.State -ne 'INTENTIONAL' }
$wet = ($considered | Where-Object { $_.State -eq 'WET' }).Count
$dry = ($considered | Where-Object { $_.State -eq 'DRY' }).Count
Write-Host ("  slots inspected: {0}  wet: {1}  dry: {2}  intentional-dry: {3}" -f `
    $considered.Count, $wet, $dry, ($rows.Count - $considered.Count))

$gaps = $considered | Where-Object { $_.State -eq 'DRY' } | Sort-Object Mesh
if (-not $gaps) { Write-Host "`nNo uncovered weapon/attachment slots."; return }

Write-Host ("`nUncovered slots, grouped by mesh ({0} meshes):" -f ($gaps.Mesh | Sort-Object -Unique).Count)
foreach ($g in ($gaps | Group-Object Mesh | Sort-Object Name)) {
    Write-Host ("`n" + ($g.Name -replace '^/Game/Weapons/', ''))
    foreach ($r in $g.Group) { Write-Host ("    " + ($r.Material -replace '^/Game/Weapons/', '')) }
}
if ($OnlyDry) { return }
Write-Host "`nSlots skipped as intentional (hands, optics glass/reticle, muzzle cavity):"
$rows | Where-Object { $_.State -eq 'INTENTIONAL' } | Group-Object Material |
    Sort-Object Name | ForEach-Object { Write-Host ("    " + ($_.Name -replace '^/Game/Weapons/', '')) }
