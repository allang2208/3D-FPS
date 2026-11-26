#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillRules.h"
#include "ColdSteelSpellRewards.h"
#include "NetCastUtils.h"
#include "ShadowStepWeapon.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Multiplayer/UppercutStaminaReceipt.h"
#include "../Movement/FPSExhaustionComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

FShadowStepCast UColdSteelStatusModel::ShadowStepStats(int32 AtLevel) const
{
    const auto& D=MasteryDefinition(ShadowStep::SkillId);
    auto C=ShadowStep::Evaluate(D.ShadowStep,AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,D.MaxLevel);
    const auto Grip=ShadowStepWeapon::ResolveGrip(this);
    const auto M=ColdSteelMelee::ItemModifiers(Grip.Primary,this);
    C.CooldownSeconds*=float(M.MartialCooldownMultiplier());
    double StaminaMul=M.Stamina;
    if(Grip.bDualWield&&Grip.Secondary)
    {
        const auto M2=ColdSteelMelee::ItemModifiers(Grip.Secondary,this);
        StaminaMul=.5*(M.Stamina+M2.Stamina);
    }
    C.StaminaCost=UEagleTalonGuardComponent::Ready(this,Grip.Primary)?0.f:float(ColdSteelMelee::ModifiedAttackStamina(C.StaminaCost,StaminaMul,
        ColdSteelMelee::TemporaryModifiers(this).Stamina,this));
    return C;
}

bool UColdSteelStatusModel::CommitShadowStepCast(const FShadowStepCast& Cast)
{
    if(!ShadowStepWeapon::Supports(this)||
        MasteryProgress(ShadowStep::SkillId).Level<1||ShadowStepCooldown()>0.f)return false;
    if(CurrentPawn.IsValid()&&!CurrentPawn->HasAuthority())return false;
    if(!CanSpendStamina(Cast.StaminaCost)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    const float Before=Current.Stamina;
    auto* Exhaustion=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Before);
    Current.Stamina=FMath::Max(0.f,Current.Stamina-Cast.StaminaCost);
    Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(Current.Stamina<=0.f)Current.bSprintExhausted=true;
    Current.UppercutStaminaSpent+=FMath::Max(0.f,Before-Current.Stamina);
    Current.ShadowStepCooldown=HasNoAbilityCooldown()?0.f:Cast.CooldownSeconds;
    Current.ShadowStepCooldownDuration=Current.ShadowStepCooldown;
    Current.MartialCooldownRevision=FMath::Min(Current.MartialCooldownRevision,MAX_int64-1)+1;
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    OnStaminaChanged.Broadcast();return true;
}

void UColdSteelStatusModel::ApplyShadowStepReceipt(double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt)
{
    auto* Exhaustion=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    if(TotalSpent>Current.UppercutStaminaSpent){UppercutStaminaReceipt::Merge(Current,TotalSpent);DelayStaminaRecovery();}
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    if(Revision>=Current.MartialCooldownRevision)
    {
        const auto* GS=GetWorld()?GetWorld()->GetGameState():nullptr;
        const double Now=GS?GS->GetServerWorldTimeSeconds():ServerAt;
        Current.ShadowStepCooldown=NetCast::RemainingCooldown(Cooldown,ServerAt,Now);
        Current.ShadowStepCooldownDuration=Duration;Current.MartialCooldownRevision=Revision;
    }
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    OnStaminaChanged.Broadcast();
}

void UColdSteelStatusModel::TrainShadowStep(int32 Kills)
{
    const auto& D=MasteryDefinition(ShadowStep::SkillId);
    if(MasteryProgress(D.Id).Level<1||MasteryProgress(D.Id).Level>=D.MaxLevel)return;
    const int32 XP=ColdSteelSpellRewards::MartialKillTrainingExperience(D,Kills,D.ShadowStep.MultiKillExperience);
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);StageTraining(MoveTemp(P));
}
