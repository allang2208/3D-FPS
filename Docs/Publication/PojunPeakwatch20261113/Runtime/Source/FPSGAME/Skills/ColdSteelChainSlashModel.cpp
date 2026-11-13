#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillRules.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/PojunGrip.h"
#include "../Multiplayer/UppercutStaminaReceipt.h"
#include "../Movement/FPSExhaustionComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

FChainSlashCast UColdSteelStatusModel::ChainSlashStats(int32 AtLevel) const
{
    const auto& D=MasteryDefinition(TEXT("chainSlash"));
    auto C=ChainSlash::Evaluate(D.ChainSlash,AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,D.MaxLevel);
    const auto M=ColdSteelMelee::ItemModifiers(PojunGrip::ChainSlashWeapon(this),this);
    C.CooldownSeconds*=float(M.MartialCooldownMultiplier());
    C.StaminaCost=float(ColdSteelMelee::ModifiedAttackStamina(C.StaminaCost,M.Stamina,
        ColdSteelMelee::TemporaryModifiers(this).Stamina,this));
    return C;
}

bool UColdSteelStatusModel::CommitChainSlashCast(const FChainSlashCast& Cast)
{
    if(!PojunGrip::ChainSlashWeapon(this)||
        MasteryProgress(TEXT("chainSlash")).Level<1||ChainSlashCooldown()>0.f)return false;
    if(CurrentPawn.IsValid()&&!CurrentPawn->HasAuthority())return false;
    if(!CanSpendStamina(Cast.StaminaCost)){Message=TEXT("体力不足");OnStaminaChanged.Broadcast();return false;}
    const float Before=Current.Stamina;
    auto* Exhaustion=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Before);
    Current.Stamina=FMath::Max(0.f,Current.Stamina-Cast.StaminaCost);
    Current.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;
    if(Current.Stamina<=0.f)Current.bSprintExhausted=true;
    Current.UppercutStaminaSpent+=FMath::Max(0.f,Before-Current.Stamina);
    Current.ChainSlashCooldown=HasNoAbilityCooldown()?0.f:Cast.CooldownSeconds;
    Current.ChainSlashCooldownDuration=Current.ChainSlashCooldown;
    Current.MartialCooldownRevision=FMath::Min(Current.MartialCooldownRevision,MAX_int64-1)+1;
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    OnStaminaChanged.Broadcast();return true;
}

void UColdSteelStatusModel::ApplyChainSlashReceipt(double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt)
{
    auto* Exhaustion=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSExhaustionComponent>():nullptr;
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    if(TotalSpent>Current.UppercutStaminaSpent){UppercutStaminaReceipt::Merge(Current,TotalSpent);DelayStaminaRecovery();}
    if(Exhaustion)Exhaustion->ObserveStamina(Current.Stamina);
    if(Revision>=Current.MartialCooldownRevision)
    {
        const auto* GS=GetWorld()?GetWorld()->GetGameState():nullptr;
        const double Now=GS?GS->GetServerWorldTimeSeconds():ServerAt;
        Current.ChainSlashCooldown=FMath::Max(0.f,Cooldown-float(FMath::Max(0.,Now-ServerAt)));
        Current.ChainSlashCooldownDuration=Duration;Current.MartialCooldownRevision=Revision;
    }
    bTrainingDirty=true;TrainingFlushAccumulator=0.f;
    OnStaminaChanged.Broadcast();
}

void UColdSteelStatusModel::TrainChainSlash(int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("chainSlash"));
    if(MasteryProgress(D.Id).Level<1||MasteryProgress(D.Id).Level>=D.MaxLevel)return;
    const int32 XP=D.UseExperience+FMath::Max(0,Kills)*D.KillExperience+(Kills>=2?D.ChainSlash.MultiKillExperience:0);
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);StageTraining(MoveTemp(P));
}
