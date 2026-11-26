#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/PojunGrip.h"
#include "ColdSteelSkillRules.h"
#include "ColdSteelSpellRewards.h"
#include "WhirlwindWeapon.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"

FWhirlwindCast UColdSteelStatusModel::WhirlwindStats(int32 AtLevel) const
{
    const auto& D=MasteryDefinition(TEXT("whirlwind"));const auto& T=D.Whirlwind;
    const int32 L=FMath::Clamp(AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,1,D.MaxLevel);
    FWhirlwindCast C;
    C.DamageMultiplier=T.DamageBase+L*T.DamagePerLevel;
    C.CooldownSeconds=FMath::Max(0.f,T.CooldownBase-L*T.CooldownReduction)*float(ColdSteelMelee::EquippedModifiers(this).MartialCooldownMultiplier());
    C.StaminaCost=FMath::Max(0.f,T.StaminaBase+L*T.StaminaPerLevel);
    C.RadiusCM=(T.RadiusBase+L*T.RadiusPerLevel+T.MeleeRadiusBonus)*T.UnitsToCM;
    C.KnockbackCM=T.Knockback*T.UnitsToCM;C.StunSeconds=T.StunSeconds;
    const auto* Tool=ActiveProductionTool();
    const auto* Item=Tool?Tool:WhirlwindWeapon::Resolve(this);
    if(Item&&((Tool&&PojunGrip::UsesHammerMotion(*Item))||(!Tool&&ColdSteelInventory::IsMeleeWeapon(*Item))))
    {
        const auto Stats=ColdSteelMelee::Evaluate(*Item,this);
        C.DamageMultiplier+=float(Stats.Modifiers.WhirlwindDamageAdd);
        C.StaminaCost*=Stats.Modifiers.Stamina*ColdSteelMelee::TemporaryModifiers(this).Stamina;
        C.Damage=FMath::RoundToFloat(Stats.Damage*C.DamageMultiplier)*Stats.Modifiers.MartialDamage;
        C.RadiusCM*=Stats.Modifiers.Range*Stats.Modifiers.MartialRange;
        C.KnockbackCM*=Stats.Modifiers.AllAttackKnockback;
        C.CooldownSeconds=FMath::Max(0.f,T.CooldownBase-L*T.CooldownReduction)*float(Stats.Modifiers.MartialCooldownMultiplier());
    }
    C.StaminaCost=UEagleTalonGuardComponent::Ready(this,Item)?0.f:C.StaminaCost*ActionStaminaMultiplier();
    return C;
}

FWhirlwindCast UColdSteelStatusModel::ZhufengWhirlwindStats() const
{
    // Keep the existing area and impact properties. Damage and payment belong
    // to dash attack, including its level, crafting and martial modifiers.
    FWhirlwindCast C=WhirlwindStats();
    const FDashAttackCast Dash=DashAttackStats();
    C.DamageMultiplier=Dash.DamageMultiplier;C.Damage=Dash.Damage;
    C.StaminaCost=Dash.StaminaCost;C.CooldownSeconds=0.f;
    return C;
}

float UColdSteelStatusModel::WhirlwindCooldown() const
{return HasNoAbilityCooldown()?0.f:Current.WhirlwindCooldown;}

bool UColdSteelStatusModel::CommitWhirlwindCast(const FWhirlwindCast& Cast,bool FromZhufengDash)
{
    const auto* Tool=ActiveProductionTool();
    const auto* Item=Tool?Tool:FromZhufengDash?Equipped():WhirlwindWeapon::Resolve(this);
    // The dash variant never checks, starts, clears or publishes the active
    // whirlwind cooldown. Sprint readiness is owned by the attack executor.
    if(FromZhufengDash)
    {
        if(Tool||!Item||!ColdSteelModularSword::UsesZhufengWhirlwind(*Item)||
            MasteryProgress(TEXT("dashAttack")).Level<1)return false;
        return SpendStamina(DashAttackStats().StaminaCost);
    }
    if(!Item||(Tool?!PojunGrip::UsesHammerMotion(*Item):!ColdSteelInventory::IsMeleeWeapon(*Item))||
        MasteryProgress(TEXT("whirlwind")).Level<1||WhirlwindCooldown()>0.f)return false;
    if(!CanSpendStamina(Cast.StaminaCost)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    SyncRuntime();auto P=Snapshot();
    P.Stamina=FMath::Max(0.f,P.Stamina-Cast.StaminaCost);
    P.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(P.Stamina<=0.f)P.bSprintExhausted=true;
    // Like the source skill, the cost and cooldown are committed once at entry.
    P.WhirlwindCooldown=HasNoAbilityCooldown()?0.f:Cast.CooldownSeconds;
    P.WhirlwindCooldownDuration=P.WhirlwindCooldown;
    P.MartialCooldownRevision=FMath::Min(P.MartialCooldownRevision,MAX_int64-1)+1;
    if(!CommitState(P))return false;
    SyncMartialCooldowns(true);OnStaminaChanged.Broadcast();return true;
}

void UColdSteelStatusModel::TrainWhirlwind(int32 Hits,int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("whirlwind"));
    const int32 XP=ColdSteelSpellRewards::MartialHitTrainingExperience(D,Hits,Kills);
    if(XP<=0||MasteryProgress(D.Id).Level>=D.MaxLevel)return;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);StageTraining(MoveTemp(P));
}
