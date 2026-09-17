#pragma once
#include "GunsmithSystem.h"
#include "../Combat/WeaponDamageTypes.h"

class UColdSteelStatusModel;

/** One evaluation for gameplay, inventory tooltips and transient gunsmith previews. */
struct FMeleeWeaponStats
{
    FMeleeModifiers Modifiers;
    double Damage=55, AttackRate=1, AttackSeconds=1.775, ThrustSeconds=1;
    double ComboSecondDamage=55, ComboThirdDamage=55;
    double HeavyMultiplier=2.5;
    double KnockbackCM=0;
    FWeaponDamageParts DamageParts;
    double ParrySeconds=1;
    double BaseReach=180, SlashReach=360, ThrustReach=360, AttackStamina=0, BlockStamina=20, BlockReduction=.5;
};

namespace ColdSteelMelee
{
    FMeleeModifiers EquippedModifiers(const UColdSteelStatusModel* Profile);
    FMeleeModifiers TemporaryModifiers(const UColdSteelStatusModel* Profile);
    FMeleeWeaponStats Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview=nullptr);
    double AttackStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile);
    // The stamina modifier covers all attacks (including heavy attacks) and blocked hits.
    double BlockStamina(const FMeleeModifiers& Modifiers);
}
