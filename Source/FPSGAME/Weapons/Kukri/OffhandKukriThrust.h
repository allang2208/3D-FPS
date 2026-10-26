#pragma once
#include "CoreMinimal.h"
#include "../MeleeWeaponStats.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../UI/ColdSteelStatusModel.h"

// Pistol + off-hand kukri quick melee (F, OffhandKukriStrike.cpp): one left-hand thrust.  The client and the
// authority (ColdSteelPlayerState: damage branch, attack form) share this pair test and damage formula.
namespace OffhandKukriThrust
{
    /** Share of the off-hand weapon's physical panel (base + added) the thrust deals before the skill's own damage. */
    inline constexpr double WeaponShare=2.;

    /** The item is the off-hand one-handed melee in the paired slot beside a main-hand dual-capable pistol. */
    inline bool IsOffhandThrust(const UColdSteelStatusModel* Profile,const FColdSteelItem* Item)
    {
        if(!Profile||!Item||!ColdSteelInventory::IsOneHandedMelee(*Item))return false;
        const auto State=Profile->Snapshot();
        const auto* Offhand=Profile->Equipped(State.ActiveWeaponSlot==6?8:11);
        const auto* Primary=Profile->Equipped(State.ActiveWeaponSlot);
        return Offhand&&Offhand->InstanceId==Item->InstanceId&&Primary&&ColdSteelInventory::IsDualPistol(*Primary);
    }

    /**
     * 200 % of the off-hand blade's physical panel, scaled by the quick-melee damage bonuses, plus the quick-melee
     * skill's own damage (5 + level + strength x (1 + 0.02 x level)): the blade sets the floor, training the skill
     * raises it like every other weapon's F.
     */
    inline float Damage(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile)
    {
        const auto Melee=ColdSteelMelee::Evaluate(Item,Profile);
        const auto Quick=Profile->QuickCombatStats();
        return float(WeaponShare*(Melee.DamageParts.BasePhysical+Melee.DamageParts.AddedPhysical))*Quick.DamageMultiplier+Quick.Damage;
    }
}
