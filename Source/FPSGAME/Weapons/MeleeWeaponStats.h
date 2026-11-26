#pragma once
#include "GunsmithSystem.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Skills/ColdSteelSkillTypes.h"

class UColdSteelStatusModel;

/** One evaluation for gameplay, inventory tooltips and transient gunsmith previews. */
struct FMeleeWeaponStats
{
    FMeleeModifiers Modifiers;
    double Damage=55, AttackRate=1, AttackSeconds=1.775, ThrustSeconds=1;
    double PhysicalAttack=0.;
    // Player-facing speed relative to this item's unmodified attack_seconds.
    // AttackRate remains the shared animation clock, not a displayed multiplier.
    double AttackSpeedMultiplier(const FColdSteelItem& Item) const;
    double ComboSecondDamage=55, ComboThirdDamage=55;
    double HeavyMultiplier=2.5;
    double KnockbackCM=0;
    FQuickCombatCast QuickCombat;
    FWeaponDamageParts DamageParts;
    double ParrySeconds=1;
    double BaseReach=180, SlashReach=360, ThrustReach=360, AttackStamina=0, BlockStamina=20, BlockReduction=.5;
    double HeavyChargeSpeedBonus=0,HeavyChargeSeconds=2;
};

namespace ColdSteelMelee
{
    /**
     * 单手近战（尼泊尔弯刀）相对双手武器的体力消耗比例。
     * 用户 2026-10-22 指定：单手刀按双手武器的一半结算。
     * 只作用于 IsOneHandedMelee()，不影响双手剑／双手钝器／采集工具／法杖。
     */
    inline constexpr double OneHandedStaminaRatio=.5;
    double UppercutMultiplier(const UColdSteelStatusModel* Profile,const FMeleeModifiers& Modifiers,int32 Level=-1);
    double UppercutReachCM(const UColdSteelStatusModel* Profile,int32 Level=-1);
    FMeleeModifiers EquippedModifiers(const UColdSteelStatusModel* Profile);
    FMeleeModifiers ItemModifiers(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile);
    // The active set's other blade only; never an inactive loadout or the same item twice.
    const FColdSteelItem* PairedOneHandedWeapon(const FColdSteelItem* Main,const UColdSteelStatusModel* Profile);
    // Quick melee uses the active weapon, or the left blade beside a pistol.
    FMeleeModifiers QuickCombatModifiers(const UColdSteelStatusModel* Profile);
    FMeleeModifiers TemporaryModifiers(const UColdSteelStatusModel* Profile);
    FMeleeWeaponStats Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview=nullptr);
    // Shared final cost for ordinary attacks/harvesting. Multipliers are applied
    // once, with at least 20% of the action's base cost remaining.
    double ModifiedAttackStamina(double BaseCost,double WeaponMultiplier,double TemporaryMultiplier,const UColdSteelStatusModel* Profile);
    double AttackStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile,const FMeleeModifiers* PreviewModifiers=nullptr,bool NormalAttack=true);
    double ComboAttackStamina(const FColdSteelItem* Main,const UColdSteelStatusModel* Profile,bool BothBlades,bool NormalAttack=true);
    double HeavyReleaseStamina(const FColdSteelItem* Item,const UColdSteelStatusModel* Profile,bool BothBlades=false);
    double HeavyChargeSeconds(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,bool BothBlades=false);
    double UnarmedAttackStamina(const UColdSteelStatusModel* Profile);
    // 防御受击耐力只吃 BlockStamina 独立乘区，不再跟随全局 Stamina。
    double BlockStamina(const FMeleeModifiers& Modifiers,const UColdSteelStatusModel* Profile=nullptr);
}
