#include "FPSHolyLightComponent.h"
#include "FPSHolyLightEffect.h"
#include "HolyLightTargets.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"

UFPSHolyLightComponent::UFPSHolyLightComponent(){PrimaryComponentTick.bCanEverTick=true;}
void UFPSHolyLightComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    MoteSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/HolyLight/NS_HolyLightMotes.NS_HolyLightMotes"));
    CastSounds.Add(LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/HolyLight/S_HolyLightCast.S_HolyLightCast")));
}
UColdSteelStatusModel* UFPSHolyLightComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSHolyLightComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSHolyLightComponent::IsTarget(AActor* Target) const
{
    return HolyLightTargets::IsAlive(Target)&&(HolyLightTargets::IsFriendly(Target)||Target->FindComponentByClass<UMonsterCombatComponent>());
}
bool UFPSHolyLightComponent::VisibleFrom(AActor* Origin,AActor* Target,const FVector& Start) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HolyLightSight),true,Origin);Query.AddIgnoredActor(GetOwner());Query.AddIgnoredActor(Target);
    FHitResult Hit;return !GetWorld()->LineTraceSingleByChannel(Hit,Start,Target->GetActorLocation(),ECC_Visibility,Query);
}
AActor* UFPSHolyLightComponent::SelectTarget(const FHolyLightCast& Spell,FString& Failure) const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return nullptr;
    const FVector Eye=Camera->GetComponentLocation(),Forward=Camera->GetForwardVector();
    AActor* Best=nullptr;double Score=DBL_MAX;bool NearAim=false,InRange=false;
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        AActor* Target=*It;if(Target==GetOwner()||!IsTarget(Target))continue;
        const FVector Offset=Target->GetActorLocation()-Eye;const double Along=FVector::DotProduct(Offset,Forward);
        if(Along<=0)continue;
        const double Perpendicular=(Offset-Forward*Along).Size();if(Perpendicular>Spell.AimRadius)continue;
        NearAim=true;if(FVector::Dist(GetOwner()->GetActorLocation(),Target->GetActorLocation())>Spell.Range)continue;
        InRange=true;if(!VisibleFrom(GetOwner(),Target,Eye))continue;
        const double CandidateScore=Perpendicular/FMath::Max(1.,Along);
        if(CandidateScore<Score){Score=CandidateScore;Best=Target;}
    }
    Failure=Best?TEXT(""):!NearAim?TEXT("准星附近无目标"):!InRange?TEXT("超出施法距离"):TEXT("目标被遮挡");return Best;
}
void UFPSHolyLightComponent::Feedback(const FString& Text){Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+2;}
void UFPSHolyLightComponent::RejectHeldHand(){bQueued=false;HandNotice.Show(GetWorld()->GetTimeSeconds());}
bool UFPSHolyLightComponent::IsHandOccupiedNotice() const{return GetWorld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());}
float UFPSHolyLightComponent::HandNoticeAlpha() const{return GetWorld()?HandNotice.Alpha(GetWorld()->GetTimeSeconds()):0;}
float UFPSHolyLightComponent::HandNoticeRise() const{return GetWorld()?HandNotice.Rise(GetWorld()->GetTimeSeconds()):0;}
FString UFPSHolyLightComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bQueued)return TEXT("等待左手");if(bCommitted)return TEXT("施法");
    if(auto* M=Model();M&&M->HolyLightCooldown()>0)return FString::Printf(TEXT("%.1f"),M->HolyLightCooldown());return TEXT("");
}
float UFPSHolyLightComponent::CooldownFraction() const
{const auto* M=Model();return M?FMath::Clamp(M->HolyLightCooldown()/FMath::Max(.1f,M->HolyLightCooldownDuration()),0.f,1.f):0;}
void UFPSHolyLightComponent::Trigger(bool bSelf)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!Player||!M||!Player->IsLocallyControlled()||GetWorld()->GetNetMode()!=NM_Standalone)return;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(bCommitted)return;
    if(Player->IsLeftHandHeldForCast()){RejectHeldHand();return;}
    if(M->HolyLightCooldown()>0){Feedback(TEXT("冷却"));return;}
    if(!MoteSystem||CastSounds.Num()!=1||CastSounds.Contains(nullptr)){Feedback(TEXT("缺素材"));return;}
    const auto Spell=M->HolyLightStats();FString Failure;
    if(!bSelf&&!SelectTarget(Spell,Failure)){Feedback(Failure);return;}
    if(!M->CanSpendMana(Spell.ManaCost)){Feedback(TEXT("缺蓝"));return;}
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    bQueuedSelf=bSelf;bQueued=true;MessageUntil=0;ServiceQueue();
}
void UFPSHolyLightComponent::ServiceQueue()
{
    if(!bQueued)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!Player||!M||!H)return;
    if(Player->IsLeftHandHeldForCast()){RejectHeldHand();return;}
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()){bQueued=false;return;}
    if(H->BlocksNewLeftHandAction()||Player->IsLeftHandBusyForCast())return;
    const auto Spell=M->HolyLightStats();FString Failure;AActor* Target=bQueuedSelf?Player:SelectTarget(Spell,Failure);
    if(!Target){bQueued=false;Feedback(Failure);return;}
    if(M->HolyLightCooldown()>0||!M->CanSpendMana(Spell.ManaCost)){bQueued=false;Feedback(TEXT("未就绪"));return;}
    // Freeze the gesture choice with the actual committed target, including
    // queued Alt self-casts. Other targets keep the shared outward palm push.
    if(!H->TryBeginSpellGesture(this,true,Spell.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::ReleaseAtContact),Target==Player))return;
    bQueued=false;
    const float BeforeMana=M->Snapshot().Mana;
    if(!M->BeginHolyLightCast(Spell)){H->CancelSpellGesture(this);return;}
    H->RecordGesturePayment(BeforeMana,M->Snapshot().Mana,true);
    CastSnapshot=Spell;LockedTarget=Target;bCommitted=true;MessageUntil=0;
    if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
}
void UFPSHolyLightComponent::ReleaseAtContact()
{
    if(!bCommitted)return;bCommitted=false;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    AActor* Target=LockedTarget.Get();LockedTarget.Reset();
    if(!Player||!M||!Camera||!IsTarget(Target)||(Target!=Player&&(FVector::Dist(Player->GetActorLocation(),Target->GetActorLocation())>CastSnapshot.Range||!VisibleFrom(Player,Target,Camera->GetComponentLocation()))))
    {if(M)M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("holyLight"));Feedback(TEXT("目标已失效或被遮挡"));return;}
    for(const auto& Sound:CastSounds)if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound.Get(),Target->GetActorLocation());
    FHolyLightRewards Rewards;
    if(HolyLightTargets::IsFriendly(Target))
    {M->ApplyHolyLightHealing(Target,CastSnapshot,Rewards);Feedback(TEXT("圣光治疗"));}
    else M->ApplyHolyLightHit(Player,Target,Camera->GetComponentLocation(),CastSnapshot,CastSnapshot.Damage,Rewards);
    FActorSpawnParameters P;P.Owner=Player;P.Instigator=Player;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Effect=GetWorld()->SpawnActor<AFPSHolyLightEffect>(Target->GetActorLocation(),FRotator::ZeroRotator,P))
    {Effect->InitializeLight(Target,MoteSystem,CastSnapshot);Effects.Add(Effect);}
    M->FinishHolyLightCast(Rewards);
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Player))
    {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
}
void UFPSHolyLightComponent::Cancel()
{
    bQueued=false;bCommitted=false;LockedTarget.Reset();
    if(auto* H=Hands())H->CancelSpellGesture(this);
    for(auto& Arc:Effects)if(Arc.IsValid())Arc->Destroy();Effects.Reset();
}
void UFPSHolyLightComponent::InterruptPending()
{
    if(bCommitted)Feedback(TEXT("施法中断"));
    bQueued=bCommitted=false;LockedTarget.Reset();
    // Healing/damage and an already released light keep their own lifetime.
}
void UFPSHolyLightComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    {if(bCommitted)if(auto* M=Model())M->RefundUnreleasedCast(Hands()?Hands()->TakeGesturePayment():0.f,TEXT("holyLight"));Cancel();return;}
    if(bCommitted&&(!Hands()||!Hands()->IsSpellGesture(this))){bCommitted=false;LockedTarget.Reset();}
    Effects.RemoveAll([](const auto& A){return !A.IsValid();});ServiceQueue();
}
void UFPSHolyLightComponent::EndPlay(EEndPlayReason::Type Reason){Cancel();Super::EndPlay(Reason);}
