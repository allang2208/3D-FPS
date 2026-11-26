#pragma once
#include "CoreMinimal.h"

struct FColdSteelItem;
class FJsonObject;

/** Rarity belongs only to non-equipment items; processing/affix quality is independent. */
namespace ColdSteelItemRarity
{
    bool IsEquipment(const FJsonObject& Data);
    bool IsEquipment(const FColdSteelItem& Item);
    struct FEnhancementLootTier
    {
        int32 MinimumLevel;
        const TCHAR* ColorKey;
        float Height, BeamIntensity, CenterIntensity;
    };
    const FEnhancementLootTier& EnhancementLootTier(int32 Level);
    bool Normalize(FColdSteelItem& Item);
    bool Normalize(TArray<FColdSteelItem>& Items);
}
