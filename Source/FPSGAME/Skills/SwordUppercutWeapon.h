#pragma once
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "../Weapons/WoodenTorchItem.h"

// The same weapon owns the uppercut's cost, release receipt, range and hit on both peers.
namespace SwordUppercutWeapon
{
    inline const FColdSteelItem* Resolve(const UColdSteelStatusModel* Profile)
    {
        // Main hand empty: the lone off-hand kukri / hatchet casts it (ActiveKukriWeapon, left hand).
        const auto* Main=Profile?Profile->ActiveKukriWeapon():nullptr;
        if(!Main)return nullptr;
        const bool Staff=ColdSteelInventory::UsesStaffMelee(*Main);
        if(!Staff&&!ColdSteelInventory::IsDualPistol(*Main))return Main;
        const auto* Off=Profile->Equipped(Profile->Snapshot().ActiveWeaponSlot==6?8:11);
        return Off&&(Staff?ColdSteelInventory::IsOneHandedBlade(*Off):ColdSteelInventory::IsOneHandedMelee(*Off))?Off:Main;
    }
    inline bool IsStaffBlade(const UColdSteelStatusModel* Profile,const FColdSteelItem* Item)
    {
        const auto* Main=Profile?Profile->Equipped():nullptr;
        const auto* Resolved=Main&&ColdSteelInventory::UsesStaffMelee(*Main)?Resolve(Profile):nullptr;
        return Item&&Resolved&&Item->InstanceId==Resolved->InstanceId&&ColdSteelInventory::IsOneHandedBlade(*Item);
    }
    inline bool Supports(const UColdSteelStatusModel* Profile,const FColdSteelItem* Item)
    {
        return Item&&!ColdSteelInventory::IsWoodenTorch(*Item)&&(ColdSteelInventory::IsTwoHandedSword(*Item)||ColdSteelInventory::IsOneHandedMelee(*Item)||IsStaffBlade(Profile,Item));
    }
}
