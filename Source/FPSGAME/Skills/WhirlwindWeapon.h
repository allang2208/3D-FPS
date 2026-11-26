#pragma once
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Weapons/WoodenTorchItem.h"

// The staff carries; the offhand blade owns the active whirlwind's stats and receipt.
namespace WhirlwindWeapon
{
    inline const FColdSteelItem* Resolve(const UColdSteelStatusModel* Profile)
    {
        // Main hand empty: the lone off-hand kukri / hatchet spins (ActiveKukriWeapon, left hand).
        const auto* Main=Profile?Profile->ActiveKukriWeapon():nullptr;
        if(!Main||!ColdSteelInventory::UsesStaffMelee(*Main))return Main;
        const auto* Off=Profile->Equipped(Profile->Snapshot().ActiveWeaponSlot==6?8:11);
        return Off&&ColdSteelInventory::IsOneHandedBlade(*Off)?Off:Main;
    }
    inline bool IsStaffBlade(const UColdSteelStatusModel* Profile,const FColdSteelItem* Item)
    {
        const auto* Main=Profile?Profile->Equipped():nullptr;
        const auto* Off=Main&&ColdSteelInventory::UsesStaffMelee(*Main)?Resolve(Profile):nullptr;
        return Item&&Off&&Item->InstanceId==Off->InstanceId&&ColdSteelInventory::IsOneHandedBlade(*Item);
    }
}
