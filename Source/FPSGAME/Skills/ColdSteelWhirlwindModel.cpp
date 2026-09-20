#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillRules.h"
#include "../Weapons/MeleeWeaponStats.h"

FWhirlwindCast UColdSteelStatusModel::WhirlwindStats(int32 AtLevel) const
{
    const auto& D=MasteryDefinition(TEXT("whirlwind"));const auto& T=D.Whirlwind;
    const int32 L=FMath::Clamp(AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,1,D.MaxLevel);
    FWhirlwindCast C;
    C.DamageMultiplier=T.DamageBase+L*T.DamagePerLevel;
    C.CooldownSeconds=FMath::Max(0.f,T.CooldownBase-L*T.CooldownReduction);
    C.StaminaCost=FMath::Max(0.f,T.StaminaBase+L*T.StaminaPerLevel);
    C.RadiusCM=(T.RadiusBase+L*T.RadiusPerLevel+T.MeleeRadiusBonus)*T.UnitsToCM;
    C.KnockbackCM=T.Knockback*T.UnitsToCM;C.StunSeconds=T.StunSeconds;
    const auto* Item=Equipped();
    if(Item&&!ActiveProductionTool()&&ColdSteelInventory::IsMeleeWeapon(*Item))
    {
        const auto Stats=ColdSteelMelee::Evaluate(*Item,this);
        C.Damage=FMath::RoundToFloat(Stats.Damage*C.DamageMultiplier);
        C.RadiusCM*=Stats.Modifiers.Range;
    }
    return C;
}

float UColdSteelStatusModel::WhirlwindCooldown() const
{return HasNoAbilityCooldown()?0.f:Current.WhirlwindCooldown;}

bool UColdSteelStatusModel::CommitWhirlwindCast(const FWhirlwindCast& Cast)
{
    const auto* Item=Equipped();
    if(!Item||ActiveProductionTool()||!ColdSteelInventory::IsMeleeWeapon(*Item)||
        MasteryProgress(TEXT("whirlwind")).Level<1||WhirlwindCooldown()>0.f)return false;
    if(!CanSpendStamina(Cast.StaminaCost)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    SyncRuntime();auto P=Snapshot();
    P.Stamina=FMath::Max(0.f,P.Stamina-Cast.StaminaCost);
    P.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(P.Stamina<=0.f)P.bSprintExhausted=true;
    // Like the source skill, the cost and cooldown are committed once at entry.
    P.WhirlwindCooldown=HasNoAbilityCooldown()?0.f:Cast.CooldownSeconds;
    P.WhirlwindCooldownDuration=P.WhirlwindCooldown;
    if(!CommitState(P))return false;
    OnStaminaChanged.Broadcast();return true;
}

void UColdSteelStatusModel::TrainWhirlwind(int32 Hits,int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("whirlwind"));
    const int32 XP=Hits*D.HitExperience+(Hits>=2?D.MultiHitExperience:0)+Kills*D.KillExperience;
    if(XP<=0||MasteryProgress(D.Id).Level>=D.MaxLevel)return;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);CommitState(P);
}
