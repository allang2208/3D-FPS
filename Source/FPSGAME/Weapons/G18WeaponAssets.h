#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace G18WeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_g18");
    inline constexpr const TCHAR* Root = TEXT("/Game/Weapons/G18/Integrated20260929");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/G18/Integrated20260929/Single/SK_G18_Manny.SK_G18_Manny");
    inline constexpr const TCHAR* WetMaterials = TEXT("/Game/Weapons/G18/Integrated20260929/DA_G18_WetMaterials");
    inline bool Matches(const USkeletalMeshComponent* Mesh)
    {
        return Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("/Weapons/G18/"));
    }
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return FString::Printf(TEXT("%s/Single/Animations/A_G18_%s.A_G18_%s"), Root, Clip, Clip);
    }
    inline FString DualRoot(int32 Side) { return FString::Printf(TEXT("%s/Dual/%s"), Root, Side ? TEXT("l") : TEXT("r")); }
    inline FString DualStem(int32 Side) { return FString::Printf(TEXT("Dual_G18_%s"), Side ? TEXT("l") : TEXT("r")); }
    inline FString DualAnimationPath(int32 Side, const FString& Clip)
    {
        return DualRoot(Side) + TEXT("/Animations/A_") + DualStem(Side) + TEXT("_") + Clip;
    }
    inline FString AttachmentPath(const FString& Part) { return FString(Root) + TEXT("/Attachments/SM_G18_") + Part; }
    inline FString SoundPath(const FString& Cue) { return FString(Root) + TEXT("/Audio/S_G18_") + Cue; }
}
