#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/PojunGrip.h"
#include "ColdSteelSkillRules.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Multiplayer/UppercutStaminaReceipt.h"
#include "../Movement/FPSExhaustionComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

FLeapStrikeCast UColdSteelStatusModel::LeapStrikeBaseStats(int32 AtLevel) const
{
    const auto& D=MasteryDefinition(TEXT("leapStrike"));
    return LeapStrike::Evaluate(D.LeapStrike,AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,D.MaxLevel);
}

FLeapStrikeCast UColdSteelStatusModel::LeapStrikeStats(int32 AtLevel) const
{
    auto C=LeapStrikeBaseStats(AtLevel);
    const auto* Item=ActiveProductionTool();
    const auto M=ColdSteelMelee::ItemModifiers(Item&&PojunGrip::UsesHammerMotion(*Item)?Item:nullptr,this);
    C.CooldownSeconds*=float(M.MartialCooldownMultiplier());
    C.StaminaCost=float(ColdSteelMelee::ModifiedAttackStamina(C.StaminaCost,M.Stamina,
        ColdSteelMelee::TemporaryModifiers(this).Stamina,this));
    return C;
}

bool UColdSteelStatusModel::CommitLeapStrikeCast(const FLeapStrikeCast& Cast)
{
    const auto* Item=ActiveProductionTool();
    if(!Item||!PojunGrip::UsesHammerMotion(*Item)||
        MasteryProgress(TEXT("leapStrike")).Level<1||LeapStrikeCooldown()>0.f)return false;
    if(CurrentPawn.IsValid()&&!CurrentPawn->HasAuthority())return false;
    if(!CanSpendStamina(Cast.StaminaCost)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    const float Before=Current.Stamina;
    auto* Exhaustion=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Before);
    Current.Stamina=FMath::Max(0.f,Current.Stamina-Cast.StaminaCost);
    Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(Current.Stamina<=0.f)Current.bSprintExhausted=true;
    Current.UppercutStaminaSpent+=FMath::Max(0.f,Before-Current.Stamina);
    Current.LeapStrikeCooldown=HasNoAbilityCooldown()?0.f:Cast.CooldownSeconds;
    Current.LeapStrikeCooldownDuration=Current.LeapStrikeCooldown;
    Current.MartialCooldownRevision=FMath::Min(Current.MartialCooldownRevision,MAX_int64-1)+1;
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    OnStaminaChanged.Broadcast();return true;
}

void UColdSteelStatusModel::ApplyLeapStrikeReceipt(double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt)
{
    auto* Exhaustion=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    if(TotalSpent>Current.UppercutStaminaSpent){UppercutStaminaReceipt::Merge(Current,TotalSpent);DelayStaminaRecovery();}
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    if(Revision>=Current.MartialCooldownRevision)
    {
        const auto* GS=GetWorld()?GetWorld()->GetGameState():nullptr;
        const double Now=GS?GS->GetServerWorldTimeSeconds():ServerAt;
        Current.LeapStrikeCooldown=FMath::Max(0.f,Cooldown-float(FMath::Max(0.,Now-ServerAt)));
        Current.LeapStrikeCooldownDuration=Duration;Current.MartialCooldownRevision=Revision;
    }
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    OnStaminaChanged.Broadcast();
}

void UColdSteelStatusModel::TrainLeapStrike(int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("leapStrike"));
    if(MasteryProgress(D.Id).Level<1||MasteryProgress(D.Id).Level>=D.MaxLevel)return;
    const int32 XP=D.UseExperience+FMath::Max(0,Kills)*D.KillExperience+(Kills>=2?D.LeapStrike.MultiKillExperience:0);
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);StageTraining(MoveTemp(P));
}
