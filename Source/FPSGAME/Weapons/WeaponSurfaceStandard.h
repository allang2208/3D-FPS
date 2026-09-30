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
    return Base&&Base->GetOutermost()->GetFName()==MasterPackage()?Asset:nullptr;
}
}
