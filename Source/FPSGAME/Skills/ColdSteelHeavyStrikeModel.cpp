#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillRules.h"
#include "../Weapons/MeleeWeaponStats.h"

float UColdSteelStatusModel::SwordUppercutStaminaCost() const
{
    return MasteryDefinition(TEXT("swordUppercut")).UppercutStaminaCost*
        ColdSteelMelee::EquippedModifiers(this).Stamina*ColdSteelMelee::TemporaryModifiers(this).Stamina;
}

float UColdSteelStatusModel::SwordUppercutCooldown() const
{
    return HasNoAbilityCooldown()?0.f:Current.SwordUppercutCooldown;
}

bool UColdSteelStatusModel::CommitSwordUppercutRelease()
{
    const auto* Item=Equipped();
    if(!Item||ActiveProductionTool()||!ColdSteelInventory::IsTwoHandedSword(*Item)||SwordUppercutCooldown()>0.f)return false;
    const auto& D=MasteryDefinition(TEXT("swordUppercut"));
    const float StaminaCost=SwordUppercutStaminaCost();
    if(!CanSpendStamina(StaminaCost)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    // Commit the resource and cooldown together before notifying listeners.
    // Stage on the live profile: disk I/O and ApplyToPawn must not interrupt release.
    Current.Stamina=FMath::Max(0.f,Current.Stamina-StaminaCost);
    Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(Current.Stamina<=0.f)Current.bSprintExhausted=true;
    Current.SwordUppercutCooldown=HasNoAbilityCooldown()?0.f:D.UppercutCooldownSeconds;
    Current.SwordUppercutCooldownDuration=Current.SwordUppercutCooldown;
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    OnStaminaChanged.Broadcast();return true;
}

bool UColdSteelStatusModel::TrainSwordUppercut(int32 Hits,int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("swordUppercut"));
    if(MasteryProgress(D.Id).Level>=D.MaxLevel)return false;
    const int32 XP=Kills>0?D.KillExperience:Hits>0?D.HitExperience:D.UseExperience;
    SyncRuntime();auto P=Snapshot();P.Skills.FindOrAdd(D.Id);
    ColdSteelSkills::AddExperience(P,D,XP);return StageTraining(MoveTemp(P));
}

bool UColdSteelStatusModel::TrainHeavyStrike(int32 Hits,int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("heavyStrike"));
    // One completed release, one highest achieved tier. Counts are unique victims
    // from this swing's direct damage window, never poison or later attacks.
    const int32 XP=Kills>=5?D.HeavyKill5Experience:Hits>=5?D.HeavyHit5Experience:
        Kills>=2?D.HeavyKill2Experience:Hits>=2?D.HeavyHit2Experience:D.UseExperience;
    if(MasteryProgress(D.Id).Level>=D.MaxLevel)return false;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);return StageTraining(MoveTemp(P));
}
