#include "FPSIceSpikeComponent.h"
#include "FPSIceSpikeVolley.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"
#include "NiagaraSystem.h"

UFPSIceSpikeComponent::UFPSIceSpikeComponent(){PrimaryComponentTick.bCanEverTick=true;}
void UFPSIceSpikeComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    for(int32 I=1;I<=3;++I)
    {
        const FString Path=FString::Printf(TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_%02d.SM_IceSpike_%02d"),I,I);
        SpikeMeshes.Add(LoadObject<UStaticMesh>(nullptr,*Path));
    }
    ShardMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"));
    IceMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/M_IceHeart.M_IceHeart"));
    IceShellMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/M_IceShell.M_IceShell"));
    ImpactFX=LoadObject<UParticleSystem>(nullptr,TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"));
    ImpactSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"));
    Motes=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystals.NS_FrostCrystals"));
    ColdMist=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/IceSpike/FrostV2/NS_ColdMist.NS_ColdMist"));
}
UColdSteelStatusModel* UFPSIceSpikeComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSIceSpikeComponent::Hands() const {return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSIceSpikeComponent::IsPrepared() const {return Active.IsValid()&&!Active->IsFlying();}
int32 UFPSIceSpikeComponent::ActiveCount() const {return Active.IsValid()?Active->RemainingCount():0;}
void UFPSIceSpikeComponent::Feedback(const FString& Text){Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+1.5;}
void UFPSIceSpikeComponent::RejectHeldLeftHand()
{
    // Shared with the fireball: a held left hand is released by a loadout change,
    // not by waiting, so the queued gather/release is dropped with the notice.
    bQueuedGather=bQueuedRelease=false;
    if(GetWorld())HandNotice.Show(float(GetWorld()->GetTimeSeconds()));
}
bool UFPSIceSpikeComponent::IsHandOccupiedNotice() const
{ return GetWorld()&&HandNotice.Active(float(GetWorld()->GetTimeSeconds())); }
float UFPSIceSpikeComponent::HandNoticeAlpha() const
{ return GetWorld()?HandNotice.Alpha(float(GetWorld()->GetTimeSeconds())):0.f; }
float UFPSIceSpikeComponent::HandNoticeRise() const
{ return GetWorld()?HandNotice.Rise(float(GetWorld()->GetTimeSeconds())):0.f; }
FString UFPSIceSpikeComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bQueuedGather||bQueuedRelease)return TEXT("等待左手");
    if(const auto* H=Hands();H&&H->IsSpellGesture(this))
    {
        if(H->GetHandPhase()==EFireballHandPhase::Raising)return TEXT("凝聚");
        if(H->GetHandPhase()==EFireballHandPhase::ReadyingRelease||H->GetHandPhase()==EFireballHandPhase::Releasing)return TEXT("齐射");
    }
    if(IsPrepared())return TEXT("齐射");if(Active.IsValid())return TEXT("飞行");
    if(auto* M=Model();M&&M->IceSpikeCooldown()>0)return FString::Printf(TEXT("%.1f"),M->IceSpikeCooldown());return TEXT("");
}
float UFPSIceSpikeComponent::CooldownFraction() const
{auto* M=Model();return M&&!Active.IsValid()?FMath::Clamp(M->IceSpikeCooldown()/FMath::Max(.1f,M->IceSpikeCooldownDuration()),0.f,1.f):0.f;}
void UFPSIceSpikeComponent::Trigger()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!Player||!M||!Player->IsLocallyControlled()||GetWorld()->GetNetMode()!=NM_Standalone)return;
    if(auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return;
    if(auto* Sword=Player->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    // The left-hand gesture is shared with the fireball, so an akimbo off-hand
    // pistol refuses the request instead of making the spell wait for the hand.
    if(Player->IsLeftHandHeldForCast()){RejectHeldLeftHand();return;}
    if(Active.IsValid())
    {
        if(IsPrepared()&&!(Hands()&&Hands()->IsSpellGesture(this)&&(Hands()->GetHandPhase()==EFireballHandPhase::ReadyingRelease||Hands()->GetHandPhase()==EFireballHandPhase::Releasing)))bQueuedRelease=true;
    }
    else
    {
        if(M->IceSpikeCooldown()>0){Feedback(TEXT("冷却"));return;}
        if(!M->CanSpendMana(M->IceSpikeStats().ManaCost)){Feedback(TEXT("缺蓝"));return;}
        if(SpikeMeshes.Num()!=3||SpikeMeshes.Contains(nullptr)||!ShardMesh||!IceMaterial||!IceShellMaterial||!ImpactFX||!ColdMist){Feedback(TEXT("缺素材"));return;}
        bQueuedGather=true;
    }
    ServiceQueue();
}
void UFPSIceSpikeComponent::ServiceQueue()
{
    auto* M=Model();auto* H=Hands();auto* Player=Cast<APawn>(GetOwner());if(!M||!H||!Player)return;
    // A loadout change while queued drops the request instead of holding it.
    if((bQueuedGather||bQueuedRelease)&&Cast<AFPSGAMECharacter>(Player)&&Cast<AFPSGAMECharacter>(Player)->IsLeftHandHeldForCast())
    {RejectHeldLeftHand();return;}
    if(bQueuedGather)
    {
        const auto Snapshot=M->IceSpikeStats();
        if(M->IceSpikeCooldown()>0||!M->CanSpendMana(Snapshot.ManaCost)){bQueuedGather=false;Feedback(TEXT("未就绪"));return;}
        if(!H->TryBeginSpellGesture(this,false,Snapshot.CastSpeed,FSimpleDelegate()))return;
        bQueuedGather=false;
        FActorSpawnParameters Params;Params.Owner=Player;Params.Instigator=Player;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Volley=GetWorld()->SpawnActor<AFPSIceSpikeVolley>(Player->GetActorLocation(),FRotator::ZeroRotator,Params);
        if(!Volley){H->CancelSpellGesture(this);return;}
        if(!M->BeginIceSpikeCast(Snapshot)){Volley->Destroy();H->CancelSpellGesture(this);return;}
        if(auto* Status=Player->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
        Active=Volley;Volley->Prepare(this,Player,Snapshot,SpikeMeshes,ShardMesh,IceMaterial,IceShellMaterial,ImpactFX,ImpactSound,Motes,ColdMist);
        MessageUntil=0;return;
    }
    if(bQueuedRelease)
    {
        if(!IsPrepared()){bQueuedRelease=false;return;}
        if(H->TryBeginSpellGesture(this,true,Active->CastSpeed(),FSimpleDelegate::CreateUObject(this,&ThisClass::LaunchAtContact)))
        {bQueuedRelease=false;MessageUntil=0;}
    }
}
void UFPSIceSpikeComponent::LaunchAtContact()
{
    if(!IsPrepared())return;
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const FVector Eye=Camera->GetComponentLocation(),End=Eye+Camera->GetForwardVector()*20000;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceSpikeAim),true,GetOwner());Query.AddIgnoredActor(Active.Get());FHitResult Hit;
    GetWorld()->LineTraceSingleByChannel(Hit,Eye,End,ECC_Visibility,Query);
    Active->Launch(Hit.bBlockingHit?Hit.ImpactPoint:End);
}
void UFPSIceSpikeComponent::VolleyFinished(AFPSIceSpikeVolley* Volley)
{if(Active.Get()!=Volley)return;Active.Reset();bQueuedRelease=false;bAimPreview=false;if(auto* H=Hands())H->CancelSpellGesture(this);}
void UFPSIceSpikeComponent::SetAimPreview(bool bActive)
{
    // Only a hovering, fully gathered group previews; during the gather the press keeps its
    // old meaning (queue the release) so the first press is never swallowed.
    const bool bRaising=Hands()&&Hands()->IsSpellGesture(this)&&Hands()->GetHandPhase()==EFireballHandPhase::Raising;
    bAimPreview=bActive&&IsPrepared()&&!bRaising;
    if(auto* V=Active.Get())V->SetAimPreviewActive(bAimPreview);
}
void UFPSIceSpikeComponent::Cancel()
{bQueuedGather=bQueuedRelease=false;bAimPreview=false;if(Active.IsValid())Active->Destroy();Active.Reset();if(auto* H=Hands())H->CancelSpellGesture(this);}
void UFPSIceSpikeComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(auto* H=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead()){Cancel();return;}
    ServiceQueue();
}
void UFPSIceSpikeComponent::EndPlay(EEndPlayReason::Type Reason){Cancel();Super::EndPlay(Reason);}
