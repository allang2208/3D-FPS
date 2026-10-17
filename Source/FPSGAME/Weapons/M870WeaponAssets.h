#pragma once
#include "CoreMinimal.h"

namespace M870WeaponAssets
{
inline constexpr const TCHAR* Definition=TEXT("ue_m870");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/M870/Tactical20261015/SK_M870_V7.SK_M870_V7");
inline constexpr double MinimumAttackInterval=.30;
inline constexpr float FireDuration=.90f;
inline constexpr float PumpPull=.16f;
inline constexpr float PumpEject=.35f;
inline constexpr float PumpPush=.40f;
inline constexpr float PumpClosed=.62f;
inline constexpr float ReloadClosed=6.62f;
inline FString AnimationPath(const TCHAR* Role)
{
    return FString::Printf(TEXT("/Game/Weapons/M870/Tactical20261015/Animations/A_M870_%s.A_M870_%s"),Role,Role);
}
inline FString SoundPath(const TCHAR* Role)
{
    return FString::Printf(TEXT("/Game/Weapons/M870/Tactical20261015/Audio/S_M870_%s.S_M870_%s"),Role,Role);
}
}
