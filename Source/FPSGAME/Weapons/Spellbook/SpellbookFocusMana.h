#pragma once
#include "../../UI/ColdSteelInventoryTypes.h"

namespace SpellbookFocusMana
{
// A reliable hit receipt and a later profile mirror may contain the same charge.
// The tagged field travels with the mana snapshot, including in-flight uploads.
inline void Merge(FColdSteelProfile& Profile,double Total)
{
    if(!FMath::IsFinite(Total)||Total<=Profile.SpellbookFocusManaLoss)return;
    Profile.Mana=float(FMath::Max(0.0,double(Profile.Mana)-(Total-Profile.SpellbookFocusManaLoss)));
    Profile.SpellbookFocusManaLoss=Total;
}
}
