#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace PitViper2011WeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_pit_viper2011");
    inline constexpr const TCHAR* Root = TEXT("/Game/Weapons/PitViper2011/Integrated20261002");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/PitViper2011/Integrated20261002/Single/SK_PitViper2011_Manny.SK_PitViper2011_Manny");
    inline bool Matches(const USkeletalMeshComponent* Mesh)
    {
        const auto* Asset = Mesh ? Mesh->GetSkeletalMeshAsset() : nullptr;
        return Asset && Asset->GetPathName().Contains(TEXT("/Weapons/PitViper2011/"));
    }
    inline FString AttachmentPath(const FString& Part)
    {
        return TEXT("/Game/Weapons/PitViper2011/Attachments20261002/SM_PitViper2011_") + Part;
    }
    // Conservative initial envelope; this has not been measured in a runtime test.
    inline constexpr float ViewmodelBoundsScale = 5.f;
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return FString::Printf(TEXT("%s/Single/Animations/A_PitViper2011_%s.A_PitViper2011_%s"), Root, Clip, Clip);
    }
    inline FString DualRoot(int32 Side) { return FString::Printf(TEXT("%s/Dual/%s"), Root, Side ? TEXT("l") : TEXT("r")); }
    inline FString DualStem(int32 Side) { return FString::Printf(TEXT("Dual_PitViper2011_%s"), Side ? TEXT("l") : TEXT("r")); }
    inline FString DualAnimationPath(int32 Side, const FString& Clip)
    {
        return DualRoot(Side) + TEXT("/Animations/A_") + DualStem(Side) + TEXT("_") + Clip;
    }
    inline FString SoundPath(const FString& Cue) { return FString(Root) + TEXT("/Audio/S_PitViper2011_") + Cue; }
}
