#include "ColdSteelPlayerState.h"
#include "../Skills/LightningHasteSpeed.h"
#include "UppercutStaminaReceipt.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/RuneSwordUppercutMotion.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Movement/FPSExhaustionComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

bool AColdSteelPlayerState::RequestSwordUppercutRelease()
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Model?Model->Equipped():nullptr;
    // The kukri's uppercut uses the same release receipt (one-handed melee, KukriUppercut.cpp).
    if(!GetPawn()||!Item||!(ColdSteelInventory::IsTwoHandedSword(*Item)||ColdSteelInventory::IsOneHandedMelee(*Item)))return false;
    ++UppercutSequence;if(!UppercutSequence)++UppercutSequence;
    // Same actor channel as ServerReportHit: payment is ordered before contact.
    // The owner applies the confirmed cost once, matching the hammer receipt.
    UppercutPawn=GetPawn();ServerSwordUppercut(UppercutSequence,GetPawn(),Item->InstanceId,false);return true;
}
void AColdSteelPlayerState::FinishSwordUppercut()
{ServerSwordUppercut(UppercutSequence,GetPawn(),FString(),true);}

void AColdSteelPlayerState::ServerSwordUppercut_Implementation(uint32 Sequence,APawn* ActionPawn,const FString& Weapon,bool Finish)
{
    if(!HasAuthority())return;
    if(Finish)
    {
        if(Sequence==UppercutActiveSequence&&ActionPawn==UppercutPawn.Get())SettleSwordUppercut();
        return;
    }
    if(!Sequence||static_cast<int32>(Sequence-UppercutReceivedSequence)<=0)return;
    UppercutReceivedSequence=Sequence;
    TickSwordUppercut();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());
    const auto* Item=ShadowModel?ShadowModel->Equipped():nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* GS=GetWorld()->GetGameState();
    const double Clock=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    const auto Reply=[&](bool Accepted)
    {
        const auto State=ShadowModel?ShadowModel->Snapshot():FColdSteelProfile();
        ClientSwordUppercutResult(Sequence,ActionPawn,Accepted,State.UppercutStaminaSpent,State.SwordUppercutCooldown,
            State.SwordUppercutCooldownDuration,State.MartialCooldownRevision,Clock);
    };
    if(UppercutActiveSequence||IsSwordWhirlwindExecuting(Pawn)||!Pawn||Pawn!=ActionPawn||!ShadowModel||!Health||Health->IsDead()
        ||!Item||Item->InstanceId!=Weapon||!(ColdSteelInventory::IsTwoHandedSword(*Item)||ColdSteelInventory::IsOneHandedMelee(*Item))
        ||ShadowModel->ActiveProductionTool()
        ||Pawn->IsTraversing()||Pawn->IsDodging()||Pawn->IsSliding()||UBoundCongregateCaptureComponent::IsCaptured(Pawn))
    {Reply(false);return;}
    const float Before=ShadowModel->Stamina();
    if(!ShadowModel->CommitSwordUppercutRelease()){Reply(false);return;}
    ShadowModel->Current.UppercutStaminaSpent+=FMath::Max(0.f,Before-ShadowModel->Stamina());
    UppercutActiveSequence=Sequence;UppercutPawn=Pawn;UppercutWeapon=Weapon;UppercutRewardModel=ShadowModel;
    UppercutHits=UppercutKills=0;bUppercutContact=false;
    UppercutUntil=GetWorld()->GetTimeSeconds()+(RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)
        -RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::ReleaseStart))/LightningHaste::ActionSpeed(Pawn)+.35;
    bServerDirty=true;Reply(true);
}

void AColdSteelPlayerState::SettleSwordUppercut()
{
    if(!HasAuthority()||!UppercutActiveSequence)return;
    auto* Model=UppercutRewardModel.Get();const int32 Hits=UppercutHits,Kills=UppercutKills;
    UppercutActiveSequence=0;UppercutUntil=0.;UppercutWeapon.Reset();UppercutRewardModel=nullptr;
    UppercutHits=UppercutKills=0;bUppercutContact=false;
    if(Model)Model->TrainSwordUppercut(Hits,Kills);
    bServerDirty=true;
}
void AColdSteelPlayerState::TickSwordUppercut()
{
    if(!UppercutActiveSequence)return;
    const auto* Pawn=UppercutPawn.Get();const auto* HP=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Item=UppercutRewardModel?UppercutRewardModel->Equipped():nullptr;
    if(!Pawn||Pawn!=GetPawn()||(HP&&HP->IsDead())||!Item||Item->InstanceId!=UppercutWeapon||GetWorld()->GetTimeSeconds()>=UppercutUntil)
        SettleSwordUppercut();
}
void AColdSteelPlayerState::ClientSwordUppercutResult_Implementation(uint32 Sequence,APawn* ActionPawn,bool Accepted,
    double TotalSpent,float Cooldown,float Duration,int64 Revision,double ServerAt)
{
    if(HasAuthority()||!Sequence||static_cast<int32>(Sequence-UppercutReceiptSequence)<=0)return;
    UppercutReceiptSequence=Sequence;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetPawn());auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Pawn||Pawn!=ActionPawn||!Pawn->IsLocallyControlled()||!Model)return;
    if(Accepted)
    {
        auto* Exhaustion=Pawn->FindComponentByClass<UFPSExhaustionComponent>();
        if(Exhaustion)Exhaustion->ObserveStamina(Model->Current.Stamina);
        UppercutStaminaReceipt::Merge(Model->Current,TotalSpent);Model->DelayStaminaRecovery();
        if(Model->Current.Stamina<=0.f)Model->Current.bSprintExhausted=true;
        if(Exhaustion)Exhaustion->ObserveStamina(Model->Current.Stamina);
    }
    const auto* GS=GetWorld()->GetGameState();const double Now=GS?GS->GetServerWorldTimeSeconds():ServerAt;
    Model->Current.SwordUppercutCooldown=FMath::Max(0.f,Cooldown-float(FMath::Max(0.,Now-ServerAt)));
    Model->Current.SwordUppercutCooldownDuration=Duration;
    Model->Current.MartialCooldownRevision=FMath::Max(Model->Current.MartialCooldownRevision,Revision);
    Model->OnStaminaChanged.Broadcast();
    if(!Accepted&&Sequence==UppercutSequence)
    {
        if(auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>())Sword->CancelAction();
        if(auto* Kukri=Pawn->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsUppercutActive())Kukri->CancelAction();
        Model->PostNotice(TEXT("上挑未执行"),TEXT("服务器体力、冷却或装备状态不满足条件"));
    }
}
