#pragma once
#include "CoreMinimal.h"
#include "DanWesson715WeaponAssets.h"

namespace RSH12WeaponAssets
{
    inline constexpr const TCHAR* Definition = TEXT("ue_rsh12");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/RSH12/SK_RSH12_Manny.SK_RSH12_Manny");
    inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials.DA_RSH12_WetMaterials");
    inline constexpr int32 Capacity = 5;
    inline FString DualMeshPath(int32 Side)
    {
        const TCHAR* Hand = Side ? TEXT("l") : TEXT("r");
        return FString::Printf(TEXT("/Game/Weapons/RSH12/Dual/%s/SK_Dual_RSH12_%s.SK_Dual_RSH12_%s"), Hand, Hand, Hand);
    }
    inline constexpr float CockLatch = .60f;
    inline constexpr float FireCycle = 1.f;
    inline constexpr float AimLowerBegin = .14f;
    inline constexpr float AimLowerEnd = .30f;
    inline constexpr float AimReturnBegin = .78f;
    inline float CockAimProgress(float SourceTime)
    {
        // UpdateCamera smooths this once, matching the authored pose curve.
        const float Lower = FMath::Clamp((SourceTime - AimLowerBegin)
            / (AimLowerEnd - AimLowerBegin), 0.f, 1.f);
        const float Return = FMath::Clamp((SourceTime - AimReturnBegin)
            / (FireCycle - AimReturnBegin), 0.f, 1.f);
        return 1.f - Lower * (1.f - Return);
    }
    inline constexpr const TCHAR* ProfilePath = TEXT("/Game/Weapons/RSH12/SingleAction20261003/Profiles/DA_RSH12_base");
    inline FString DualProfilePath(int32 Side)
    {
        return FString::Printf(TEXT("/Game/Weapons/RSH12/SingleAction20261003/Profiles/DA_RSH12_%s_base"),Side?TEXT("l"):TEXT("r"));
    }
    inline FString DualFirePath(int32 Side)
    {
        const TCHAR* Hand=Side?TEXT("l"):TEXT("r");
        return FString::Printf(TEXT("/Game/Weapons/RSH12/SingleAction20261003/%s/A_RSH12_%s_fire"),Hand,Hand);
    }
    // Fire/cock has its own source duration; the rest of the 715 family stays shared.
    inline FString AnimationPath(const TCHAR* Clip)
    {
        if(FCString::Strcmp(Clip,TEXT("fire"))==0 || FCString::Strcmp(Clip,TEXT("aim_fire"))==0)
            return FString::Printf(TEXT("/Game/Weapons/RSH12/SingleAction20261003/single/A_RSH12_%s"),Clip);
        return DanWesson715WeaponAssets::AnimationPath(Clip);
    }
}
