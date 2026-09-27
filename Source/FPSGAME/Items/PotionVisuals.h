#pragma once

#include "CoreMinimal.h"

/** Shared bottle geometry for ground pickups and first-person potion use. */
struct FPotionTierVisual
{
    FString Tier;
    TArray<FString> Definitions;
    FString Shell, Liquid, Stopper, Closed;
    float HeightCm=18.f;
    float GripHeightCm=13.2f;
};

namespace PotionVisuals
{
    const TArray<FPotionTierVisual>& Tiers();
    int32 FindTier(const FString& Definition);
    const FString& LiquidMaterial(bool bMana);
}
