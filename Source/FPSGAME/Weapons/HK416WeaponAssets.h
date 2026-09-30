#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace HK416WeaponAssets
{
inline constexpr const TCHAR* Definition = TEXT("ue_hk416");
inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny.SK_HK416_Manny");
inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials");
inline bool Matches(const USkeletalMeshComponent* Component)
{
    return Component && Component->GetSkeletalMeshAsset()
        && Component->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/HK416/Reworked20260930/"));
}
inline FString AnimationPath(const TCHAR* Clip, const TCHAR* Family = TEXT("base"))
{
    return FString::Printf(TEXT("/Game/Weapons/HK416/Reworked20260930/Animations/%s/A_HK416_%s_%s.A_HK416_%s_%s"), Family, Family, Clip, Family, Clip);
}
inline FString AttachmentPath(const FString& Part)
{
    return FString::Printf(TEXT("/Game/Weapons/HK416/Reworked20260930/Attachments/SM_HK416_%s.SM_HK416_%s"), *Part, *Part);
}
}
