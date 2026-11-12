#pragma once
#include "CoreMinimal.h"

namespace LMGStabilityGrip
{
inline constexpr const TCHAR* Id=TEXT("lmg_stability_foregrip");
inline constexpr double FullBonusSeconds = 1.5;
inline constexpr float MaxBonusStabilityPoints = 15.f;
inline float AdditionalRecoilMultiplier(float Alpha)
{
    // The installed handling already includes 0.85. At full charge the
    // grip contributes 0.70 overall, independent of other attachments.
    return FMath::Lerp(1.f, 0.70f / 0.85f, Alpha);
}
inline constexpr const TCHAR* HandguardProfile=TEXT("/Game/Weapons/LMGStabilityGrip20261111/DA_M249_Handguard");
inline bool Supports(const FString& Definition)
{return Definition==TEXT("ue_m249")||Definition==TEXT("ue_lmg201")||Definition==TEXT("ue_pkm_lowpoly");}
inline FString MeshPath(const FString& Definition)
{
    const TCHAR* Family=Definition==TEXT("ue_m249")?TEXT("M249"):Definition==TEXT("ue_lmg201")?TEXT("LMG201"):TEXT("PKM");
    return FString(TEXT("/Game/Weapons/LMGStabilityGrip20261111/SM_"))+Family+TEXT("_StabilityGrip");
}
inline FString ProfilePath(const FString& Definition)
{return FString(TEXT("/Game/Weapons/LMGStabilityGrip20261111/DA_"))+(Definition==TEXT("ue_lmg201")?TEXT("LMG201"):TEXT("PKM"))+TEXT("_Stability");}
}
