#include "FPSLightningComponent.h"
#include "FPSLightningArc.h"
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

UFPSLightningComponent::UFPSLightningComponent(){PrimaryComponentTick.bCanEverTick=true;}
void UFPSLightningComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    ArcSystem=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"));
    for(int32 I=1;I<=2;++I)CastSounds.Add(LoadObject<USoundBase>(nullptr,*FString::Printf(TEXT("/Game/Skills/Lightning/S_LightningCast%d.S_LightningCast%d"),I,I)));
}
UColdSteelStatusModel* UFPSLightningComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSLightningComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSLightningComponent::IsTarget(AActor* Target) const
{
    const auto* C=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    return Target!=GetOwner()&&C&&!C->IsDead()&&!Target->ActorHasTag(TEXT("Friendly"));
}
bool UFPSLightningComponent::VisibleFrom(AActor* Origin,AActor* Target,const FVector& Start) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(LightningSight),true,Origin);Query.AddIgnoredActor(GetOwner());Query.AddIgnoredActor(Target);
    FHitResult Hit;return !GetWorld()->LineTraceSingleByChannel(Hit,Start,Target->GetActorLocation(),ECC_Visibility,Query);
}
AActor* UFPSLightningComponent::SelectTarget(const FLightningCast& Spell,FString& Failure) const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return nullptr;
    const FVector Eye=Camera->GetComponentLocation(),Forward=Camera->GetForwardVector();
    AActor* Best=nullptr;double Score=DBL_MAX;bool NearAim=false,InRange=false;
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        AActor* Target=*It;if(!IsTarget(Target))continue;
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
void UFPSLightningComponent::Feedback(const FString& Text){Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+2;}
void UFPSLightningComponent::RejectHeldHand(){bQueued=false;HandNotice.Show(GetWorld()->GetTimeSeconds());}
bool UFPSLightningComponent::IsHandOccupiedNotice() const{return GetWorld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());}
float UFPSLightningComponent::HandNoticeAlpha() const{return GetWorld()?HandNotice.Alpha(GetWorld()->GetTimeSeconds()):0;}
float UFPSLightningComponent::HandNoticeRise() const{return GetWorld()?HandNotice.Rise(GetWorld()->GetTimeSeconds()):0;}
FString UFPSLightningComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bQueued)return TEXT("等待左手");if(bCommitted)return TEXT("施法");
    if(auto* M=Model();M&&M->LightningCooldown()>0)return FString::Printf(TEXT("%.1f"),M->LightningCooldown());return TEXT("");
}
float UFPSLightningComponent::CooldownFraction() const
{const auto* M=Model();return M?FMath::Clamp(M->LightningCooldown()/FMath::Max(.1f,M->LightningCooldownDuration()),0.f,1.f):0;}
void UFPSLightningComponent::Trigger()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!Player||!M||!Player->IsLocallyControlled()||GetWorld()->GetNetMode()!=NM_Standalone)return;
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(bCommitted)return;
    if(Player->IsLeftHandHeldForCast()){RejectHeldHand();return;}
    if(M->LightningCooldown()>0){Feedback(TEXT("冷却"));return;}
    if(!ArcSystem||CastSounds.Num()!=2||CastSounds.Contains(nullptr)){Feedback(TEXT("缺素材"));return;}
    const auto Spell=M->LightningStats();FString Failure;
    if(!SelectTarget(Spell,Failure)){Feedback(Failure);return;}
    if(!M->CanSpendMana(Spell.ManaCost)){Feedback(TEXT("缺蓝"));return;}
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    bQueued=true;MessageUntil=0;ServiceQueue();
}
void UFPSLightningComponent::ServiceQueue()
{
    if(!bQueued)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!Player||!M||!H)return;
    if(Player->IsLeftHandHeldForCast()){RejectHeldHand();return;}
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored()){bQueued=false;return;}
    if(H->BlocksNewLeftHandAction()||Player->IsLeftHandBusyForCast())return;
    const auto Spell=M->LightningStats();FString Failure;AActor* Target=SelectTarget(Spell,Failure);
    if(!Target){bQueued=false;Feedback(Failure);return;}
    if(M->LightningCooldown()>0||!M->CanSpendMana(Spell.ManaCost)){bQueued=false;Feedback(TEXT("未就绪"));return;}
    if(!H->TryBeginSpellGesture(this,true,Spell.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::ReleaseAtContact)))return;
    bQueued=false;
    if(!M->BeginLightningCast(Spell)){H->CancelSpellGesture(this);return;}
    CastSnapshot=Spell;LockedTarget=Target;bCommitted=true;MessageUntil=0;
    if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
}
void UFPSLightningComponent::SpawnArc(const FVector& Start,const FVector& End,float Width,bool bOverload)
{
    FActorSpawnParameters P;P.Owner=GetOwner();P.Instigator=Cast<APawn>(GetOwner());P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Arc=GetWorld()->SpawnActor<AFPSLightningArc>(Start,FRotator::ZeroRotator,P))
    {
        auto Visual=CastSnapshot;if(bOverload){Visual.Duration=.45f;Visual.Fade=.22f;Visual.Segments=8;Visual.Jitter=.11f;}
        Arc->InitializeArc(ArcSystem,Start,End,Visual,Width);Arcs.Add(Arc);
    }
}
void UFPSLightningComponent::Overload(AActor* Origin,FLightningRewards& Rewards)
{
    auto* Player=Cast<APawn>(GetOwner());auto* M=Model();if(!Origin||!Player||!M)return;
    if(auto* C=Origin->FindComponentByClass<UMonsterCombatComponent>())C->ReceiveStun(Player,CastSnapshot.OverloadStun,0);
    const FVector Start=Origin->GetActorLocation();
    // Source intent is hostile-to-caster. The old target-faction comparison could shock the player.
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        AActor* Target=*It;
        if(Target==Origin||!IsTarget(Target)||FVector::Dist(Start,Target->GetActorLocation())>CastSnapshot.OverloadRange||!VisibleFrom(Origin,Target,Start))continue;
        SpawnArc(Start,Target->GetActorLocation(),.45f,true);
        M->ApplyLightningHit(Player,Target,Start,CastSnapshot,CastSnapshot.OverloadDamage,Rewards,false);
    }
}
void UFPSLightningComponent::ReleaseAtContact()
{
    if(!bCommitted)return;bCommitted=false;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    AActor* First=LockedTarget.Get();LockedTarget.Reset();
    if(!Player||!M||!Camera||!IsTarget(First)||FVector::Dist(Player->GetActorLocation(),First->GetActorLocation())>CastSnapshot.Range||!VisibleFrom(Player,First,Camera->GetComponentLocation()))
    {Feedback(TEXT("目标已失效或被遮挡"));return;}
    TArray<TWeakObjectPtr<AActor>> Chain;Chain.Add(First);AActor* Cursor=First;
    while(Chain.Num()<CastSnapshot.Count)
    {
        AActor* Best=nullptr;float Distance=CastSnapshot.ChainRange;
        for(TActorIterator<AActor> It(GetWorld());It;++It)
        {
            AActor* Target=*It;if(!IsTarget(Target)||Chain.Contains(Target))continue;
            const float D=FVector::Dist(Cursor->GetActorLocation(),Target->GetActorLocation());
            if(D<=Distance&&VisibleFrom(Cursor,Target,Cursor->GetActorLocation())){Distance=D;Best=Target;}
        }
        if(!Best)break;Chain.Add(Best);Cursor=Best;
    }
    for(const auto& Sound:CastSounds)if(Sound)UGameplayStatics::PlaySoundAtLocation(this,Sound.Get(),Player->GetActorLocation());
    FVector Start=Camera->GetComponentLocation()+Camera->GetForwardVector()*45-Camera->GetRightVector()*22-Camera->GetUpVector()*20;
    TArray<USkeletalMeshComponent*> Meshes;Player->GetComponents(Meshes);
    for(auto* Skel:Meshes)
        if(Skel&&Skel->IsVisible()&&Skel->DoesSocketExist(TEXT("hand_l")))
        {Start=Skel->GetSocketLocation(TEXT("hand_l"));break;}
    FLightningRewards Rewards;
    for(int32 I=0;I<Chain.Num();++I)
    {
        AActor* Target=Chain[I].Get();if(!IsTarget(Target))continue;
        const FVector End=Target->GetActorLocation();const float Decay=FMath::Pow(1-CastSnapshot.ChainDecay,I);
        SpawnArc(Start,End,.75f+.25f*Decay);
        if(M->ApplyLightningHit(Player,Target,Start,CastSnapshot,FMath::FloorToFloat(CastSnapshot.Damage*Decay),Rewards))
            if(auto* C=Target->FindComponentByClass<UMonsterCombatComponent>();C&&!C->IsDead())
            {
                auto* Status=UCombatStatusFormula::GetOrAdd(Target);
                if(!Status->IsImmune())
                {
                    C->ReceiveStun(Player,CastSnapshot.StunSeconds,0);
                    if(Status->AddElectrified(CastSnapshot.ElectrifyStacks,CastSnapshot.ElectrifyDuration,CastSnapshot.OverloadStacks,CastSnapshot.ElectricBonusPerStack))Overload(Target,Rewards);
                }
            }
        Start=End;
    }
    M->FinishLightningCast(Rewards);
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Player))
    {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
}
void UFPSLightningComponent::Cancel()
{
    bQueued=false;bCommitted=false;LockedTarget.Reset();
    if(auto* H=Hands())H->CancelSpellGesture(this);
    for(auto& Arc:Arcs)if(Arc.IsValid())Arc->Destroy();Arcs.Reset();
}
void UFPSLightningComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead()){Cancel();return;}
    if(bCommitted&&(!Hands()||!Hands()->IsSpellGesture(this))){bCommitted=false;LockedTarget.Reset();}
    Arcs.RemoveAll([](const auto& A){return !A.IsValid();});ServiceQueue();
}
void UFPSLightningComponent::EndPlay(EEndPlayReason::Type Reason){Cancel();Super::EndPlay(Reason);}
