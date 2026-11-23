#pragma once

#include "../UI/ColdSteelInventoryTypes.h"

namespace ColdSteelInventory
{
    inline constexpr const TCHAR* WoodenTorchDefinition = TEXT("ue_wooden_torch");

    inline constexpr double TorchFuelSeconds = 24. * 60.;

    inline double TorchFuelRemaining(const FColdSteelItem& Item)
    {
        return FMath::Clamp(TorchFuelSeconds - Item.TorchBurnedSeconds, 0., TorchFuelSeconds);
    }

    inline bool IsWoodenTorch(const FColdSteelItem& Item)
    {
        return Item.Definition == WoodenTorchDefinition;
    }

    inline bool UsesStaffMelee(const FColdSteelItem& Item)
    {
        return IsStaff(Item) || IsWoodenTorch(Item);
    }

    inline const FColdSteelItem* QuickTorch(const FColdSteelItem* Main,const FColdSteelItem* Off)
    {
        if (Off && IsWoodenTorch(*Off))
        {
            if (Main && IsWoodenTorch(*Main)) return Main;
            return !Main || IsStaff(*Main) || IsDualPistol(*Main) || IsAlchemySpellbook(*Main) ? Off : nullptr;
        }
        if (Main && IsWoodenTorch(*Main) && (!Off || Text(*Off,TEXT("weaponType"))==TEXT("shield") || Text(*Off,TEXT("offhandType"))==TEXT("shield")))
            return Main;
        return nullptr;
    }

    // Only an otherwise empty active set promotes its offhand torch to the primary staff rig.
    inline const FColdSteelItem* StaffMeleeItem(const FColdSteelItem* Main,const FColdSteelItem* Off)
    {
        if (Main) return UsesStaffMelee(*Main) ? Main : nullptr;
        return Off && IsWoodenTorch(*Off) ? Off : nullptr;
    }
}
