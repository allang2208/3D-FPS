#pragma once
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "../Weapons/WoodenTorchItem.h"

// Unified 4-grip resolver for ShadowStepSlash (瞬步掠影斩):
// 1. Main-hand single one-handed blade/hatchet (or lone offhand when main hand is empty)
// 2. Dual-wield one-handed melee (kukri/hatchet/mixed)
// 3. Pistol + offhand one-handed melee
// 4. Staff + offhand one-handed melee
// Excludes wooden torches, production tools, and all two-handed / ranged-only weapons.
namespace ShadowStepWeapon
{
    struct FResolvedGrip
    {
        const FColdSteelItem* Primary=nullptr;
        const FColdSteelItem* Secondary=nullptr;
        bool bDualWield=false;
        bool bOffhandAuxiliary=false; // Pistol+offhand or Staff+offhand
        bool bLoneOffhand=false;      // Main hand empty, offhand blade wielded directly
        bool IsValid() const { return Primary!=nullptr; }
    };

    inline bool IsEligibleItem(const FColdSteelItem* Item)
    {
        return Item && !ColdSteelInventory::IsWoodenTorch(*Item) &&
            ColdSteelInventory::IsOneHandedMelee(*Item);
    }

    inline FResolvedGrip ResolveGrip(const UColdSteelStatusModel* Profile)
    {
        FResolvedGrip Out;
        if(!Profile || Profile->ActiveProductionTool())return Out;
        const auto* EquippedMain=Profile->Equipped();
        if(!EquippedMain)
        {
            const auto* Lone=Profile->ActiveKukriWeapon();
            if(IsEligibleItem(Lone)){Out.Primary=Lone;Out.bLoneOffhand=true;}
            return Out;
        }
        if(IsEligibleItem(EquippedMain))
        {
            Out.Primary=EquippedMain;
            if(const auto* Off=ColdSteelMelee::PairedOneHandedWeapon(EquippedMain,Profile);IsEligibleItem(Off))
            {
                Out.Secondary=Off;
                Out.bDualWield=true;
            }
            return Out;
        }
        if(ColdSteelInventory::IsDualPistol(*EquippedMain)||ColdSteelInventory::UsesStaffMelee(*EquippedMain))
        {
            const auto* Off=Profile->Equipped(Profile->Snapshot().ActiveWeaponSlot==6?8:11);
            if(IsEligibleItem(Off))
            {
                Out.Primary=Off;
                Out.bOffhandAuxiliary=true;
            }
        }
        return Out;
    }

    inline const FColdSteelItem* Resolve(const UColdSteelStatusModel* Profile)
    {
        return ResolveGrip(Profile).Primary;
    }

    inline bool Supports(const UColdSteelStatusModel* Profile)
    {
        return ResolveGrip(Profile).IsValid();
    }
}
