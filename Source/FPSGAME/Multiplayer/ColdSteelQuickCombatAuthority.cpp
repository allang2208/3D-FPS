#include "ColdSteelPlayerState.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

void AColdSteelPlayerState::RequestQuickCombat(float Duration,float PredictedCost)
{
    if(QuickCombatPawn.Get()!=GetPawn())QuickCombatPredictedCosts.Reset();
    ++QuickCombatSequence;if(!QuickCombatSequence)++QuickCombatSequence;
    QuickCombatPredictedCosts.Add(QuickCombatSequence,PredictedCost);
    QuickCombatPawn=GetPawn();
    // Only one action is live. Keep recent rejected costs until its receipt arrives.
    for(auto It=QuickCombatPredictedCosts.CreateIterator();It;++It)
        if(static_cast<int32>(QuickCombatSequence-It.Key())>16)It.RemoveCurrent();
    ServerQuickCombat(QuickCombatSequence,GetPawn(),Duration,false);
}
void AColdSteelPlayerState::FinishQuickCombat()
{
    ServerQuickCombat(QuickCombatSequence,GetPawn(),0.f,true);
}
void AColdSteelPlayerState::ServerQuickCombat_Implementation(uint32 Sequence,APawn* ActionPawn,float Duration,bool Finish)
{
    if(!HasAuthority())return;
    if(Finish)
    {
        if(Sequence==QuickCombatServerSequence&&ActionPawn==QuickCombatPawn.Get())QuickCombatUntil=0.;
        return;
    }
    if(!Sequence||static_cast<int32>(Sequence-QuickCombatServerSequence)<=0)return;
    const double Now=GetWorld()->GetTimeSeconds();
    const bool Busy=Now<QuickCombatUntil;
    QuickCombatServerSequence=Sequence;QuickCombatUntil=0.;QuickCombatTargets.Reset();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Book=Pawn?Pawn->FindComponentByClass<USpellbookComponent>():nullptr;
    if(Busy||!Pawn||ActionPawn!=Pawn||!Health||Health->IsDead()||!ShadowModel
        ||!FMath::IsFinite(Duration)||Duration<.1f||Duration>5.f||Pawn->IsTraversing()
        ||(Book&&Book->IsFocusActive())||!ShadowModel->SpendStamina(ShadowModel->QuickCombatStaminaCost()))
    {ClientQuickCombatRejected(Sequence);return;}
    QuickCombatPawn=Pawn;QuickCombatUntil=Now+Duration+.35;
    ShadowModel->TrainQuickCombat(ShadowModel->QuickCombatDefinition().UseExperience);
}
void AColdSteelPlayerState::ClientQuickCombatRejected_Implementation(uint32 Sequence)
{
    float Cost=0.f;if(!QuickCombatPredictedCosts.RemoveAndCopyValue(Sequence,Cost))return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Pawn||Pawn!=QuickCombatPawn.Get()||!Model)return;
    Model->Current.Stamina=FMath::Min(Model->MaxStamina(),Model->Current.Stamina+Cost);
    Model->OnStaminaChanged.Broadcast();
    if(Sequence!=QuickCombatSequence)return;
    if(auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>())Quick->Cancel();
    if(auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>())Sword->CancelAction();
    Model->FinishQuickCombatCast();
    Model->PostNotice(TEXT("快速近战未执行"),TEXT("服务器角色状态或体力尚未同步"));
}
