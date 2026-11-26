#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/PojunGrip.h"
#include "ColdSteelSkillRules.h"
#include "SwordUppercutWeapon.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"

namespace
{
FMeleeModifiers UppercutModifiers(const UColdSteelStatusModel* Profile)
{
    const auto* Tool=Profile->ActiveProductionTool();
    const auto* Gunsmith=Profile->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    if(Tool&&PojunGrip::UsesHammerMotion(*Tool)&&Gunsmith)
        return Gunsmith->Calculate(Tool->Definition,Gunsmith->Installed(*Tool)).Melee;
    const auto* Item=SwordUppercutWeapon::Resolve(Profile);
    return SwordUppercutWeapon::Supports(Profile,Item)?
        ColdSteelMelee::Evaluate(*Item,Profile).Modifiers:ColdSteelMelee::EquippedModifiers(Profile);
}
}

float UColdSteelStatusModel::SwordUppercutStaminaCost() const
{
    if(UEagleTalonGuardComponent::Ready(this))return 0.f;
    return MasteryDefinition(TEXT("swordUppercut")).UppercutStaminaCost*
        UppercutModifiers(this).Stamina*ColdSteelMelee::TemporaryModifiers(this).Stamina*ActionStaminaMultiplier();
}

float UColdSteelStatusModel::SwordUppercutCooldown() const
{
    return HasNoAbilityCooldown()?0.f:Current.SwordUppercutCooldown;
}

float UColdSteelStatusModel::SwordUppercutCooldownSeconds() const
{
    return MasteryDefinition(TEXT("swordUppercut")).UppercutCooldownSeconds*
        float(UppercutModifiers(this).MartialCooldownMultiplier());
}

bool UColdSteelStatusModel::CommitSwordUppercutRelease()
{
    if(!IsSkillLearned(TEXT("swordUppercut"))){Message=TEXT("尚未习得上挑");return false;}
    const auto* Tool=ActiveProductionTool();const auto* Item=Tool?Tool:SwordUppercutWeapon::Resolve(this);
    // Two-handed sword, two-handed blunt tool, the one-handed kukri (KukriUppercut.cpp, 2026-10-23),
    // or the off-hand kukri behind a dual pistol (OffhandKukriUppercut.cpp, 2026-10-25).
    if(!Item||(Tool?!PojunGrip::UsesHammerMotion(*Item):
        !SwordUppercutWeapon::Supports(this,Item))||SwordUppercutCooldown()>0.f)return false;
    const float StaminaCost=SwordUppercutStaminaCost();
    if(!CanSpendStamina(StaminaCost)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    if(!Tool&&CurrentPawn.IsValid()&&CurrentPawn->IsLocallyControlled()&&CurrentPawn->GetNetMode()==NM_Client)
    {
        auto* PS=CurrentPawn->GetPlayerState<AColdSteelPlayerState>();
        return PS&&PS->RequestSwordUppercutRelease();
    }
    // Commit the resource and cooldown together before notifying listeners.
    // Stage on the live profile: disk I/O and ApplyToPawn must not interrupt release.
    Current.Stamina=FMath::Max(0.f,Current.Stamina-StaminaCost);
    Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(Current.Stamina<=0.f)Current.bSprintExhausted=true;
    Current.SwordUppercutCooldown=HasNoAbilityCooldown()?0.f:SwordUppercutCooldownSeconds();
    Current.SwordUppercutCooldownDuration=Current.SwordUppercutCooldown;
    Current.MartialCooldownRevision=FMath::Min(Current.MartialCooldownRevision,MAX_int64-1)+1;
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    SyncMartialCooldowns(true);OnStaminaChanged.Broadcast();return true;
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
