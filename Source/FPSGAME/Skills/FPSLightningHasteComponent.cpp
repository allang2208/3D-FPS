#include "FPSLightningHasteComponent.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "FPSFireballComponent.h"
#include "PlayerSkillPreparation.h"
#include "NetCastUtils.h"
#include "LightningHasteSpeed.h"
#include "../Combat/RangedAttackQuery.h"
#include "EnemyAttackDamage.h"
#include "HolyLightTargets.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "CorrosivePusDamage.h"
#include "Components/CapsuleComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInterface.h"
#include "Net/UnrealNetwork.h"

UFPSLightningHasteComponent::UFPSLightningHasteComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;SetIsReplicatedByDefault(true);}
UColdSteelStatusModel* UFPSLightningHasteComponent::Model() const
{return NetCast::LocalModel(*this);}
UFPSFireballComponent* UFPSLightningHasteComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
double UFPSLightningHasteComponent::Clock() const
{return GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
const FLightningHasteState& UFPSLightningHasteComponent::View() const{return bAwaiting?Prediction:State;}
float UFPSLightningHasteComponent::Remaining() const
{const auto& S=View();return S.bActive?FMath::Max(0.,S.StartedAt+S.Cast.Duration-Clock()):0.f;}
float UFPSLightningHasteComponent::ActionMultiplier() const
{return Remaining()>0?1.f+View().Cast.ActionBonus:1.f;}
float UFPSLightningHasteComponent::MoveMultiplier() const
{return Remaining()>0?1.f+View().Cast.MoveBonus:1.f;}
void UFPSLightningHasteComponent::Feedback(const TCHAR* Text){Message=Text;MessageUntil=Clock()+2.;}
bool UFPSLightningHasteComponent::IsHandOccupiedNotice() const
{const auto* P=Cast<AFPSGAMECharacter>(GetOwner());return P&&P->IsSpellHandHeld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());}
float UFPSLightningHasteComponent::HandNoticeAlpha() const{return HandNotice.Alpha(GetWorld()->GetTimeSeconds());}
float UFPSLightningHasteComponent::HandNoticeRise() const{return HandNotice.Rise(GetWorld()->GetTimeSeconds());}
FString UFPSLightningHasteComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");if(Clock()<MessageUntil)return Message;
    if(bQueued)return TEXT("等待动作");if(bCommitted)return TEXT("引雷");
    if(Remaining()>0)return FString::Printf(TEXT("迅捷 %.1fs"),Remaining());
    if(const auto* M=Model();M&&M->LightningHasteCooldown()>0)return FString::Printf(TEXT("%.1f"),M->LightningHasteCooldown());return FString();
}
float UFPSLightningHasteComponent::CooldownFraction() const
{const auto* M=Model();return M?FMath::Clamp(M->LightningHasteCooldown()/FMath::Max(.1f,M->LightningHasteCooldownDuration()),0.f,1.f):0.f;}
void UFPSLightningHasteComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())AddTickPrerequisiteComponent(Body);
    if(GetNetMode()==NM_DedicatedServer)return;
    PlayerSkillAssets::Defer(GetOwner(),TEXT("lightningHaste"),FSimpleDelegate::CreateWeakLambda(this,[this]()
    {
        ArcSystem=PlayerSkillAssets::Resolve<UNiagaraSystem>(LightningHasteAssets::Arc);
        CastSound=PlayerSkillAssets::Resolve<USoundBase>(LightningHasteAssets::CastSound);
        EndSound=PlayerSkillAssets::Resolve<USoundBase>(LightningHasteAssets::EndSound);UpdateVisuals();
    }));
}
void UFPSLightningHasteComponent::Trigger()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());if(!P||!P->IsLocallyControlled()||bCommitted)return;
    if(P->IsSpellHandHeld()){HandNotice.Show(GetWorld()->GetTimeSeconds());bQueued=false;return;}
    if(Remaining()>0){Feedback(TEXT("迅捷生效中"));return;}
    bQueued=true;ServiceQueue();
}
void UFPSLightningHasteComponent::ServiceQueue()
{
    if(!bQueued)return;auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!P||!M||!H)return;
    const auto* PC=Cast<APlayerController>(P->GetController());if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()){bQueued=false;return;}
    if(P->IsSpellHandHeld()){HandNotice.Show(GetWorld()->GetTimeSeconds());bQueued=false;return;}
    if(H->HasOtherPreparedSpell(this)){Feedback(TEXT("先释放已积蓄魔法"));bQueued=false;return;}
    if(H->BlocksNewLeftHandAction()||P->IsSpellHandBusy())return;
    if(UBoundCongregateCaptureComponent::IsCaptured(P)){Feedback(TEXT("受控"));bQueued=false;return;}
    if(const auto* S=P->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune()){Feedback(TEXT("状态免疫"));bQueued=false;return;}
    Pending=M->LightningHasteStats();
    if(M->LightningHasteCooldown()>0||!M->CanSpendMana(Pending.ManaCost)){Feedback(M->LightningHasteCooldown()>0?TEXT("冷却"):TEXT("缺蓝"));bQueued=false;return;}
    if(!H->TryBeginSpellGesture(this,false,Pending.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::Release)))return;
    bQueued=false;const float Before=M->Snapshot().Mana;
    if(!M->BeginLightningHasteCast(Pending)){H->CancelSpellGesture(this);return;}
    H->RecordGesturePayment(Before,M->Snapshot().Mana,true);bCommitted=true;PendingRefund=0;
    if(GetNetMode()==NM_Client){LocalCastId=NetCast::Send(P,TEXT("lightningHaste"),0);if(!LocalCastId){Cancel();Feedback(TEXT("联机施法未就绪"));}}
}
void UFPSLightningHasteComponent::Release()
{
    if(!bCommitted)return;
    if(const auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune()){Cancel();Feedback(TEXT("状态免疫"));return;}
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner())){Cancel();return;}
    bCommitted=false;auto* P=Cast<APawn>(GetOwner());PendingRefund=Hands()?Hands()->TakeGesturePayment():0.f;
    if(GetNetMode()==NM_Client)
    {
        NetCast::Send(P,TEXT("lightningHaste"),1,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,LocalCastId);
        Start(Pending,LocalCastId,nullptr);
    }
    else {PendingRefund=0;Start(Pending,0,NetCast::AuthorityModel(P,GetWorld()->GetGameInstance()));}
}
void UFPSLightningHasteComponent::Cancel()
{
    bQueued=false;if(!bCommitted)return;
    if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("lightningHaste"));
    if(GetNetMode()==NM_Client&&LocalCastId)NetCast::Send(GetOwner(),TEXT("lightningHaste"),2,FVector::ZeroVector,FVector::UpVector,0,nullptr,0,FVector::ForwardVector,LocalCastId);
    bCommitted=false;if(auto* H=Hands())H->CancelSpellGesture(this);Feedback(TEXT("施法中断"));
}
void UFPSLightningHasteComponent::Start(const FLightningHasteCast& Spell,uint32 CastId,UColdSteelStatusModel* OwnerModel)
{
    UCombatStatusFormula::GetOrAdd(GetOwner());
    RewardCast=Spell;Kills=0;CountedVictims.Reset();
    if(GetOwner()->HasAuthority())
    {
        RewardModel=OwnerModel;State.Cast=Spell;State.CastId=CastId;++State.Serial;State.StartedAt=Clock();State.bActive=true;
        if(OwnerModel)OwnerModel->CommitLightningHasteCast(Spell);GetOwner()->ForceNetUpdate();
    }
    else
    {
        Prediction.Cast=Spell;Prediction.CastId=CastId;Prediction.StartedAt=Clock();Prediction.bActive=true;bAwaiting=true;
        if(auto* M=Model())M->CommitLightningHasteCast(Spell);
    }
    RefreshStatus();UpdateVisuals();
    if(CastSound&&GetNetMode()!=NM_DedicatedServer)UGameplayStatics::PlaySoundAtLocation(this,CastSound,GetOwner()->GetActorLocation(),.32f,1.15f);
}
bool UFPSLightningHasteComponent::NetRelease(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* OwnerModel,const FLightningHasteCast& Spell)
{
    if(Caster!=GetOwner()||!Caster->HasAuthority()||!OwnerModel||!Req.CastId||Req.SkillId!=TEXT("lightningHaste")||Remaining()>0)return false;
    if(const auto* S=Caster->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune())return false;
    Start(Spell,Req.CastId,OwnerModel);return true;
}
void UFPSLightningHasteComponent::NetCastResult(uint8 Phase,uint8 Code,uint32 CastId)
{
    if(!CastId||CastId!=LocalCastId)return;
    if(!Code){if(Phase==1){ConfirmedCastId=CastId;PendingRefund=0;}return;}
    if(Phase>1||ConfirmedCastId==CastId||RejectedCastId==CastId)return;RejectedCastId=CastId;
    const float Refund=bCommitted&&Hands()?Hands()->TakeGesturePayment():PendingRefund;PendingRefund=0;
    if(auto* M=Model())M->RefundUnreleasedCast(Refund,TEXT("lightningHaste"));
    if(bCommitted){bCommitted=false;if(auto* H=Hands())H->CancelSpellGesture(this);}bQueued=false;
    if(bAwaiting)End(false);OnRep_State();Feedback(TEXT("施法失败"));
}
void UFPSLightningHasteComponent::OnRep_State()
{
    if(bAwaiting&&State.CastId!=LocalCastId)return;
    if(State.CastId&&State.CastId==LocalCastId){ConfirmedCastId=State.CastId;PendingRefund=0;}
    bAwaiting=false;Prediction.bActive=false;
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){End(false);return;}
    RefreshStatus();UpdateVisuals();
    const auto* P=Cast<APawn>(GetOwner());
    if(State.bActive&&Remaining()>0&&Clock()-State.StartedAt<.75&&SoundSerial!=State.Serial&&P&&!P->IsLocallyControlled()&&CastSound)
        UGameplayStatics::PlaySoundAtLocation(this,CastSound,GetOwner()->GetActorLocation(),.32f,1.15f);
    SoundSerial=State.Serial;
}
void UFPSLightningHasteComponent::RefreshStatus()
{
    auto* S=UStatusEffectsComponent::GetOrCreate(GetOwner());S->Remove(TEXT("lightningHaste"));
    if(Remaining()>0)S->SetTimed(TEXT("lightningHaste"),Remaining());
    if(auto* P=Cast<AFPSGAMECharacter>(GetOwner());P&&!P->IsActorBeingDestroyed())
    {
        auto* M=P->HasAuthority()?NetCast::AuthorityModel(P,GetWorld()->GetGameInstance()):(P->IsLocallyControlled()?Model():nullptr);
        if(M){P->ApplyColdSteelProfile(M);if(P->IsLocallyControlled())M->OnChanged.Broadcast();}
    }
}

void UFPSLightningHasteComponent::ObserveKill(AActor* Victim)
{
    if(!GetOwner()->HasAuthority()||Remaining()<=0||!IsValid(Victim)||Victim==GetOwner()||
       Victim->ActorHasTag(TEXT("NoSkillTraining"))||Victim->ActorHasTag(TEXT("Summoned"))||
       RangedAttackQuery::IsFriendlyUnit(GetOwner(),Victim)||CountedVictims.Contains(Victim))return;
    CountedVictims.Add(Victim);++Kills;
}
void UFPSLightningHasteComponent::End(bool bTrain)
{
    const bool Had=State.bActive||Prediction.bActive||RewardModel.IsValid();auto* M=RewardModel.Get();
    const int32 XP=RewardCast.CastExperience+Kills*RewardCast.KillExperience+(Kills>10?RewardCast.Kill11Bonus:Kills>5?RewardCast.Kill6Bonus:0);
    RewardModel.Reset();Kills=0;CountedVictims.Reset();bAwaiting=false;Prediction.bActive=false;
    if(State.bActive){State.bActive=false;if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();}
    if(!bTrain)ClearVisuals();
    if(auto* S=GetOwner()->FindComponentByClass<UStatusEffectsComponent>())S->Remove(TEXT("lightningHaste"));
    if(bTrain&&Had&&GetOwner()->HasAuthority()&&M)M->FinishLightningHasteTraining(XP);
    if(Had)RefreshStatus();
}
void UFPSLightningHasteComponent::FinishForRemoval(){Cancel();End(true);ClearVisuals();}
void UFPSLightningHasteComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())
    {Cancel();if(State.bActive||Prediction.bActive||RewardModel.IsValid())End(true);ClearVisuals();return;}
    if(bCommitted&&(!Hands()||!Hands()->IsSpellGesture(this)))Cancel();ServiceQueue();
    if(const auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>();S&&S->IsImmune())
    {Cancel();if(State.bActive||Prediction.bActive||RewardModel.IsValid())End(true);ClearVisuals();return;}
    if(Remaining()<=0&&(State.bActive||Prediction.bActive||RewardModel.IsValid()||bAwaiting))End(true);
    UpdateVisuals(Delta);
}
void UFPSLightningHasteComponent::EndPlay(EEndPlayReason::Type Reason){FinishForRemoval();Super::EndPlay(Reason);}
void UFPSLightningHasteComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(UFPSLightningHasteComponent,State);}

float LightningHaste::ActionSpeed(const AActor* Actor)
{
    const auto* P=Cast<AFPSGAMECharacter>(Actor);
    const auto* C=P?P->GetLightningHaste():(UnknownSpell::IsCaster(Actor)?Actor->FindComponentByClass<UFPSLightningHasteComponent>():nullptr);return C?C->ActionMultiplier():1.f;
}
float LightningHaste::MoveSpeed(const AActor* Actor)
{
    const auto* P=Cast<AFPSGAMECharacter>(Actor);
    const auto* C=P?P->GetLightningHaste():(UnknownSpell::IsCaster(Actor)?Actor->FindComponentByClass<UFPSLightningHasteComponent>():nullptr);return C?C->MoveMultiplier():1.f;
}
