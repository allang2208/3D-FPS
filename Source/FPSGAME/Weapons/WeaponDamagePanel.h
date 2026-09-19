#pragma once
#include "../Combat/WeaponDamageTypes.h"
struct FColdSteelItem;
struct FMeleeModifiers;
class UColdSteelStatusModel;

namespace ColdSteelWeaponDamage
{
    // Processed base includes existing weapon formula, enhancement, mastery and affixes.
    FWeaponDamageParts Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,double ProcessedBase,const FMeleeModifiers* Melee=nullptr);
}
