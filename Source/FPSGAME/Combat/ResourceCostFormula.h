#pragma once

#include "CoreMinimal.h"

namespace ColdSteelResourceCost
{
    inline constexpr double MaximumItemReduction=.5;
    inline constexpr double MinimumCostRatio=.2;

    // Base, enhancement and enchantment add within one equipment item.
    inline double EquipmentMultiplier(double SignedBonus)
    {
        return FMath::Max(1.-MaximumItemReduction,1.+SignedBonus);
    }

    // Apply once, after all modifier zones, including temporary effects.
    inline double Apply(double BaseCost,double CombinedMultiplier)
    {
        return FMath::Max(0.,BaseCost)*FMath::Max(MinimumCostRatio,CombinedMultiplier);
    }
}
