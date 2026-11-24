#pragma once
#include "../../UI/ColdSteelInventoryTypes.h"

namespace ColdSteelBow
{
// Flat mastery and additional damage keep their existing coefficient.
// The weapon's own dexterity and strength terms live in the weapon formula.
inline double DamageCoefficientScale(const FColdSteelItem& Item)
{
    return ColdSteelInventory::IsBow(Item)
        ? FMath::Max(0., ColdSteelInventory::Number(Item, TEXT("bow_damage_coefficient_scale"), 1.5)) : 1.;
}

// WeaponBase includes the installed bowstring's base-damage adjustment.
// Keep that adjustment on the constant term, before attributes and rounding.
inline double AdjustFormulaBase(const FColdSteelItem& Item, double FormulaBase, double WeaponBase)
{
    if (!ColdSteelInventory::IsBow(Item)) return FormulaBase;
    const double StockBase = ColdSteelInventory::Number(Item, TEXT("full_damage"), FormulaBase);
    return StockBase > 0. ? FormulaBase * (WeaponBase / StockBase) : FormulaBase;
}
}
