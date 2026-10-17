#pragma once

#include "Engine/SkinnedAssetCommon.h"
#include "Materials/MaterialInterface.h"

namespace WeaponPresentationMaterials
{
inline bool IsArmName(const FString& Value)
{
    const FString Name=Value.ToLower();
    // Handguard and firearm parts are not skin. Match explicit arm/hand names.
    return Name.Contains(TEXT("manny"))||Name==TEXT("hand")||Name==TEXT("hands")
        ||Name.EndsWith(TEXT("_hand"))||Name.EndsWith(TEXT("_hands"))
        ||Name==TEXT("arms")||Name.EndsWith(TEXT("_arms"))||Name.Contains(TEXT("_arms_"))
        ||Name==TEXT("skin_forearm")||Name==TEXT("skin_upperarm")
        ||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||Name==TEXT("skin")
        ||(Name.StartsWith(TEXT("bare"))&&(Name.Contains(TEXT("arms"))||Name.Contains(TEXT("hands"))));
}

inline bool IsArmSection(const FSkeletalMaterial& Material)
{
    // GeometryScript can replace Manny display slots with imported material
    // names. Use the authored material too, independent of clothing overrides.
    return IsArmName(Material.MaterialSlotName.ToString())
        ||(Material.MaterialInterface&&IsArmName(Material.MaterialInterface->GetName()));
}
}
