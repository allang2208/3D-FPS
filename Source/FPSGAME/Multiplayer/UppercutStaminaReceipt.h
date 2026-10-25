#pragma once
#include "../UI/ColdSteelInventoryTypes.h"

namespace UppercutStaminaReceipt
{
// Shared confirmed sword-martial ledger (uppercut and whirlwind). Keep the
// persisted field name for existing saves. RPC/mirror order cannot charge twice.
inline void Merge(FColdSteelProfile& Profile,double Total)
{
    if(!FMath::IsFinite(Total)||Total<=Profile.UppercutStaminaSpent)return;
    Profile.Stamina=float(FMath::Max(0.,double(Profile.Stamina)-(Total-Profile.UppercutStaminaSpent)));
    Profile.UppercutStaminaSpent=Total;
    if(Profile.Stamina<=0.f)Profile.bSprintExhausted=true;
}
}
