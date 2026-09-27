#pragma once
#include "../../UI/ColdSteelInventoryTypes.h"

namespace ColdSteelBow
{
// The catalog stores the scaled base (69). This scales the other additive
// coefficients once, before their existing percentage/charge multipliers.
inline double DamageCoefficientScale(const FColdSteelItem& Item)
{
    return ColdSteelInventory::IsBow(Item)
        ? FMath::Max(0., ColdSteelInventory::Number(Item, TEXT("bow_damage_coefficient_scale"), 1.5)) : 1.;
}
}
