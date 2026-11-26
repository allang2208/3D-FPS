#include "ColdSteelPlayerState.h"
#include "../Weapons/WoodenTorchItem.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/Kukri/KukriRelentlessComponent.h"
#include "../Weapons/Kukri/KukriDecisiveComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/OffhandKukriComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

FString AColdSteelPlayerState::QuickCombatEquipmentKey() const
{
    const auto* Profile=HasAuthority()?ShadowModel.Get():GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile)return FString();
    const int32 Active=Profile->Current.ActiveWeaponSlot;
    FString Key=FString::FromInt(Active);
    for(const int32 Cell:{Active,Active==6?8:11})
    {
        const auto* Item=Profile->Equipped(Cell);
        Key+=TEXT("|");
        if(Item)Key+=Item->InstanceId+TEXT(":")+Item->Definition;
    }
    return Key;
}

void AColdSteelPlayerState::RequestQuickCombat(float Duration,float PredictedCost,float PredictedMana)
{
    if(QuickCombatPawn.Get()!=GetPawn())QuickCombatPredictedCosts.Reset();
    ++QuickCombatSequence;if(!QuickCombatSequence)++QuickCombatSequence;
    QuickCombatPredictedCosts.Add(QuickCombatSequence,FVector2f(PredictedCost,PredictedMana));
    QuickCombatPawn=GetPawn();
    // Only one action is live. Keep recent rejected costs until its receipt arrives.
    for(auto It=QuickCombatPredictedCosts.CreateIterator();It;++It)
        if(static_cast<int32>(QuickCombatSequence-It.Key())>16)It.RemoveCurrent();
    ServerQuickCombat(QuickCombatSequence,GetPawn(),Duration,false,QuickCombatEquipmentKey());
}
void AColdSteelPlayerState::FinishQuickCombat()
{
    ServerQuickCombat(QuickCombatSequence,GetPawn(),0.f,true,FString());
}
bool AColdSteelPlayerState::IsQuickCombatExecuting(const APawn* Pawn) const
{
    // The extra 350 ms accepts late hit reports; it is not additional recovery.
    return Pawn&&QuickCombatPawn.Get()==Pawn&&GetWorld()&&GetWorld()->GetTimeSeconds()<QuickCombatUntil-.35;
}
void AColdSteelPlayerState::ServerQuickCombat_Implementation(uint32 Sequence,APawn* ActionPawn,float Duration,bool Finish,const FString& Equipment)
{
    if(!HasAuthority())return;
    if(Finish)
    {
        if(Sequence==QuickCombatServerSequence&&ActionPawn==QuickCombatPawn.Get())
        {
            if(GetPawn())if(auto* Pendant=GetPawn()->FindComponentByClass<UKukriDecisiveComponent>())Pendant->EndServer(1);
            QuickCombatUntil=0.;QuickCombatServerSequence=0;
            QuickCombatPawn.Reset();QuickCombatTargets.Reset();
            QuickCombatEquipment.Reset();
        }
        return;
    }
    if(!Sequence||static_cast<int32>(Sequence-QuickCombatRequestSequence)<=0)return;
    QuickCombatRequestSequence=Sequence;
    const double Now=GetWorld()->GetTimeSeconds();
    // Rejected/replayed intents cannot replace the accepted action identity,
    // deadline or already-hit targets. A previous pawn cannot occupy this life.
    const bool Busy=QuickCombatPawn.Get()==GetPawn()&&Now<QuickCombatUntil;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Book=Pawn?Pawn->FindComponentByClass<USpellbookComponent>():nullptr;
    const auto* Broken=Pawn?Pawn->FindComponentByClass<UPlayerGuardBreakComponent>():nullptr;
    const auto* Hammer=Pawn?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
    const auto* Main=ShadowModel?ShadowModel->Equipped():nullptr;
    const auto* Off=ShadowModel?ShadowModel->Equipped(ShadowModel->ActiveOffhandSlot()):nullptr;
    if(ColdSteelInventory::QuickTorch(Main,Off)&&!ShadowModel->ActiveProductionTool())
    {
        const auto* Reload=Main?PistolReloads.Find(Main->InstanceId):nullptr;
        if(HasAuthorityConsumableReservation(Pawn)||HasGenericMeleeBusy(Pawn)||
            (Reload&&Reload->Active&&Reload->Pawn.Get()==Pawn))
        {ClientQuickCombatRejected(Sequence);return;}
    }
    const float Before=ShadowModel?ShadowModel->Stamina():0.f;
    float ManaPaid=0.f;
    if(Busy||(Hammer&&Hammer->IsPojunChainOccupied())||IsSwordWhirlwindExecuting(Pawn)||!Pawn||ActionPawn!=Pawn||!Health||Health->IsDead()||!ShadowModel
        ||Equipment.IsEmpty()||Equipment!=QuickCombatEquipmentKey()
        ||!FMath::IsFinite(Duration)||Duration<.1f||Duration>5.f||Pawn->IsTraversing()||(Hammer&&Hammer->IsThunderHammerAway())
        ||(Book&&Book->IsFocusActive())||(Broken&&Broken->IsActive())||UPlayerKnockdownComponent::IsKnockedDown(Pawn)||!ShadowModel->IsSkillLearned(TEXT("quickCombat"))
        ||!ShadowModel->SpendQuickCombatResources(ShadowModel->QuickCombatStaminaCost(),ManaPaid))
    {ClientQuickCombatRejected(Sequence);return;}
    if(const auto* Item=ShadowModel->ActiveProductionTool();Item&&PojunGrip::UsesHammerMotion(*Item))
        // Only cancel this pawn's hammer. The general local-input interrupt
        // also reapplies the GameInstance profile, which belongs to the host.
        if(auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>())Tool->CancelUse();
    if(const auto* Item=ShadowModel->Equipped())
        if(auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword && Sword->HasGaleGuard(Item))
            Sword->RecordGalePayment(GaleWing::Key(GaleWing::EAttack::Quick,Sequence),Item->InstanceId,Before-ShadowModel->Stamina());
    if(const auto* Held=ShadowModel->Equipped())
        UEagleTalonGuardComponent::Commit(Pawn,Held->InstanceId,EEagleStrike::Quick,Sequence);
    QuickCombatServerSequence=Sequence;QuickCombatTargets.Reset();
    QuickCombatEquipment=Equipment;
    if(auto* Pendant=Pawn->FindComponentByClass<UKukriRelentlessComponent>())Pendant->PrepareServerAttack(1);
    if(auto* Pendant=Pawn->FindComponentByClass<UKukriDecisiveComponent>())Pendant->BeginServer(1,FString(),FString(),true,Duration);
    QuickCombatPawn=Pawn;QuickCombatUntil=Now+Duration+.35;
    ShadowModel->TrainQuickCombat(ShadowModel->QuickCombatDefinition().UseExperience);
}
void AColdSteelPlayerState::ClientQuickCombatRejected_Implementation(uint32 Sequence)
{
    FVector2f Cost=FVector2f::ZeroVector;if(!QuickCombatPredictedCosts.RemoveAndCopyValue(Sequence,Cost))return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Pawn||Pawn!=QuickCombatPawn.Get()||!Model)return;
    Model->Current.Stamina=FMath::Min(Model->MaxStamina(),Model->Current.Stamina+Cost.X);
    if(Cost.Y>0.f)Model->Current.Mana=FMath::Min(float(Model->Derived(TEXT("maxMp"))),Model->Current.Mana+Cost.Y);
    Model->OnStaminaChanged.Broadcast();
    if(Sequence!=QuickCombatSequence)return;
    // A delayed gun-melee rejection can arrive after switching weapons. Only
    // cancel a quick cast; ordinary punches and sword attacks are newer actions.
    if(auto* Quick=Pawn->FindComponentByClass<UFPSQuickCombatComponent>();
        Quick&&Quick->IsOccupyingLeftHand()&&Quick->GetStyle()!=EQuickCombatStyle::UnarmedPunch)Quick->Cancel();
    if(auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsQuickCombatActive())Sword->CancelAction();
    if(auto* Kukri=Pawn->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsQuickCombatActive())Kukri->CancelAction();
    if(auto* Offhand=Pawn->FindComponentByClass<UOffhandKukriComponent>();Offhand&&Offhand->IsQuickCombatActive())Offhand->CancelQuickCombat();
    Model->FinishQuickCombatCast();
    Model->PostNotice(TEXT("快速近战未执行"),TEXT("服务器角色状态或体力尚未同步"));
}
