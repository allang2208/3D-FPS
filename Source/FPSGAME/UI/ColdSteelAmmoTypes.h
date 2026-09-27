#pragma once
#include "CoreMinimal.h"

/** Catalog identity, not an inventory item or a world pickup. */
struct FColdSteelAmmoType
{
    FString Id, Group, GroupName, Name, Description, Icon, TierName;
    FLinearColor TierColor=FLinearColor::Transparent;
    int32 Order=0;
    bool Enabled=true;
    bool AllowInfiniteReserve=false;
    float DamageMultiplier=1.f;
    float PhysicalArmorPenetration=0.f;
    int32 PoisonStacks=0, BleedStacks=0;
    /** Optional complete arrow mesh: same 76 cm shaft/nock contact as the bow. */
    FString ProjectileMesh;
};

struct FColdSteelAmmoChoice
{
    FString Id, Name;
    int64 Count=0;
    bool Current=false;
};

namespace ColdSteelAmmo
{
    constexpr int64 MaxCount=9007199254740991ll;
}
