#pragma once

#include "CoreMinimal.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"

/** Shared weapon surface standard (Docs/Weapons/weapon-surface-standard-20260930.md).
    Materials under M_WeaponSurface carry their own WeaponWetness layer, so they need
    no dry/wet pair table: the asset-backed instance is its own wet replacement. */
namespace WeaponSurfaceStandard
{
inline const FName& MasterPackage()
{
    static const FName Name(TEXT("/Game/Weapons/WeaponSurface/Master/M_WeaponSurface"));
    return Name;
}

/** The asset instance to use as wet replacement, or null when the material is not on the standard. */
inline UMaterialInterface* SelfWetSource(UMaterialInterface* Material)
{
    UMaterialInterface* Asset=Material;
    if(const auto* MID=Cast<UMaterialInstanceDynamic>(Material))Asset=MID->Parent;
    if(!Asset||!Asset->IsAsset())return nullptr;
    const UMaterial* Base=Asset->GetBaseMaterial();
    if(!Base)return nullptr;
    const FName Package=Base->GetOutermost()->GetFName();
    // M249's regional/static graphs retain WS1 wetness; fitted optical housings
    // preserve their existing masked windows and single wet layer.
    if(Base->GetOutermost()->GetName().StartsWith(TEXT("/Game/Weapons/M249/Surface20261108/Master/")))return Asset;
    // SUPER90 rear grips use the same wet layer with a vertex-masked polymer/metal finish.
    static const FName Super90RearGripMaster(TEXT("/Game/Weapons/Super90/RearGrips20261012/Materials/M_Super90RearGripSurface"));
    // M24 keeps the shared wet layer and resolves its mixed UV0 material regions before it.
    static const FName M24SurfaceMaster(TEXT("/Game/Weapons/M24/Surface20261027/Materials/M_M24RegionalSurface"));
    static const FName M24StaticSurfaceMaster(TEXT("/Game/Weapons/M24/Surface20261027/Materials/M_M24RegionalSurface_Static"));
    static const FName M24IronSurfaceMaster(TEXT("/Game/Weapons/M24/Surface20261027/Materials/M_M24IronSurface"));
    static const FName M24ChassisSurfaceMaster(TEXT("/Game/Weapons/M24/AdvancedAction20261029/Materials/M_M24AdvancedSurface"));
    static const FName SniperStockSurfaceMaster(TEXT("/Game/Weapons/SkeletonSniperStock20261031/Materials/M_SniperStockSurface"));
    return Package==MasterPackage()||Package==Super90RearGripMaster||Package==M24SurfaceMaster||Package==M24StaticSurfaceMaster||Package==M24IronSurfaceMaster||Package==M24ChassisSurfaceMaster||Package==SniperStockSurfaceMaster?Asset:nullptr;
}
}
