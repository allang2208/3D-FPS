#pragma once
#include "CoreMinimal.h"
#include "DanWesson715WeaponAssets.h"

namespace RSH12WeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_rsh12");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny.SK_RSH12_Manny");
    inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials.DA_RSH12_WetMaterials");
    inline constexpr int32 Capacity = 5;
    inline constexpr const TCHAR* Speedloader = TEXT("rsh12_speedloader_5");
    inline FString DualMeshPath(int32 Side)
    {
        const TCHAR* Hand = Side ? TEXT("l") : TEXT("r");
        return FString::Printf(TEXT("/Game/Weapons/RSH12/Native71520261003/%s/SK_Dual_RSH12_%s.SK_Dual_RSH12_%s"), Hand, Hand, Hand);
    }
    inline constexpr float FireCycle = .4f;
    // Share 715 actions; profiles adapt the RSH mechanics and loading contacts.
    inline constexpr const TCHAR* ProfilePath = TEXT("/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base");
    inline FString DualProfilePath(int32 Side)
    {
        return FString::Printf(TEXT("/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_%s_base"),Side?TEXT("l"):TEXT("r"));
    }
    inline FString SoundPath(const TCHAR* Cue)
    {
        return FString::Printf(TEXT("/Game/Weapons/RSH12/DoubleAction20261003/Audio/S_RSH12_%s"),Cue);
    }
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return DanWesson715WeaponAssets::AnimationPath(Clip);
    }
}
