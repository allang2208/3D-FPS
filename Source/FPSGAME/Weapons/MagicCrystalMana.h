#pragma once
#include "../UI/ColdSteelInventoryTypes.h"

namespace MagicCrystalMana
{
// The total travels with Mana so receipts and delayed profile mirrors credit once.
inline void Merge(FColdSteelProfile& Profile,double Total,float Maximum)
{
    if(!FMath::IsFinite(Total)||Total<=Profile.MagicCrystalManaRestored)return;
    Profile.Mana=float(FMath::Clamp(double(Profile.Mana)+Total-Profile.MagicCrystalManaRestored,0.,double(Maximum)));
    Profile.MagicCrystalManaRestored=Total;
}
}
