#pragma once
#include "CoreMinimal.h"

namespace SniperSuppressorAssets
{
inline constexpr const TCHAR* Part=TEXT("sniper_heavy_suppressor");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/SniperSuppressor20261019/SM_SniperHeavySuppressor");
inline constexpr float TipCM=31.7f;
inline bool Supports(const FString& Definition)
{
    return Definition==TEXT("ue_svd")||Definition==TEXT("ue_svch");
}
}
