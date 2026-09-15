#include "FPSFireballComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "FPSFireballProjectile.h"
#include "FPSCastingMeshComponent.h"
#include "../Movement/FPSTraversalRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "Misc/ScopeExit.h"

UFPSFireballComponent::UFPSFireballComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    CoreAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/NS_FireballSlowBurnCore.NS_FireballSlowBurnCore")));
    TrailAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/NS_FireballVelocityTrail.NS_FireballVelocityTrail")));
    ExplosionAsset=TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic.NS_FireballImpactRealistic")));
    ShockwaveAsset=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/M_FireballHeatShockwave.M_FireballHeatShockwave")));
    ImpactSoundAsset=TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/S_FireballImpactLayered.S_FireballImpactLayered")));
}
void UFPSFireballComponent::BeginPlay()
{
    Super::BeginPlay();
    AddTickPrerequisiteActor(GetOwner());
    PoseSettings.Load();
    // Load once with the player, before the first input.
    Core=CoreAsset.LoadSynchronous();Trail=TrailAsset.LoadSynchronous();Explosion=ExplosionAsset.LoadSynchronous();
    Shockwave=ShockwaveAsset.LoadSynchronous();ImpactSound=ImpactSoundAsset.LoadSynchronous();
    if(auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>())
    {
        FallbackHands=NewObject<UFPSCastingMeshComponent>(GetOwner(),TEXT("CastingFallbackLeftArm"));
        GetOwner()->AddInstanceComponent(FallbackHands);FallbackHands->SetupAttachment(Camera);
        FallbackHands->SetRelativeRotation(FRotator(0,90,0));
        FallbackHands->SetSkeletalMesh(GetDefault<UFPSTraversalSettings>()->ArmsMesh.LoadSynchronous());
        FallbackHands->SetCollisionEnabled(ECollisionEnabled::NoCollision);FallbackHands->SetCanEverAffectNavigation(false);
        FallbackHands->SetCastShadow(false);FallbackHands->SetOnlyOwnerSee(true);FallbackHands->SetVisibility(false);
        FallbackHands->RegisterComponent();FallbackHands->SetComponentTickEnabled(false);
        FallbackHands->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
    }
}
UColdSteelStatusModel* UFPSFireballComponent::Model() const
{ return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr; }
bool UFPSFireballComponent::IsPrepared() const { return Active.IsValid()&&!Active->IsFlying(); }
bool UFPSFireballComponent::IsFlying() const { return Active.IsValid()&&Active->IsFlying(); }
void UFPSFireballComponent::SetHandPhase(EFireballHandPhase Phase)
{
    if(Phase==EFireballHandPhase::Recovering)
    {
        RecoveryReleaseAlpha=HandReleaseFraction();
        RecoveryFromPhase=HandPhase;RecoveryFromFraction=HandPhaseFraction();
    }
    HandPhase=Phase;PhaseAge=0.f;
    if(Phase==EFireballHandPhase::Raising || Phase==EFireballHandPhase::ReadyingRelease)
    { ++CastSerial;bHandEntryCaptured=false;bReleaseFromRest=Phase==EFireballHandPhase::ReadyingRelease; }
}
void UFPSFireballComponent::CaptureHandEntry(const FTransform& Hand,const FTransform& Clavicle,const FVector& Shoulder,const FVector& Elbow)
{
    if(bHandEntryCaptured)return;
    EntryHand=Hand;EntryClavicle=Clavicle;EntryShoulder=Shoulder;EntryElbow=Elbow;bHandEntryCaptured=true;
}
float UFPSFireballComponent::HandReleaseFraction() const
{
    if(HandPhase==EFireballHandPhase::Recovering)return RecoveryReleaseAlpha;
    if(HandPhase==EFireballHandPhase::ReadyingRelease)return .48f;
    if(HandPhase!=EFireballHandPhase::Releasing)return 0.f;
    const float T=PhaseAge/FMath::Max(.01f,FMath::Min(LaunchContactTime,ReleaseDuration));
    return FireballCastMotion::ReleasePalm(T,bReleaseFromRest);
}
FFireballArmMotion UFPSFireballComponent::SampleHandMotion(const FQuat& HandCorrection,const FFireballArmMotion& Current) const
{
    FFireballArmMotion Entry;
    Entry.Wrist=EntryHand.GetLocation();Entry.Rotation=EntryHand.GetRotation();
    Entry.Shoulder=EntryShoulder;Entry.Pole=EntryElbow;
    const auto Sample=[&](EFireballHandPhase Phase,float Fraction)
    {
        if(Phase==EFireballHandPhase::Raising)return FireballCastMotion::Gather(PoseSettings,Entry,HandCorrection,Fraction);
        if(Phase==EFireballHandPhase::ReadyingRelease)return FireballCastMotion::Ready(PoseSettings,Entry,HandCorrection,Fraction);
        if(Phase==EFireballHandPhase::Releasing)
            return FireballCastMotion::Release(PoseSettings,HandCorrection,
                Fraction*FMath::Max(.01f,ReleaseDuration)/FMath::Max(.01f,FMath::Min(LaunchContactTime,ReleaseDuration)),bReleaseFromRest);
        return Current;
    };
    if(HandPhase==EFireballHandPhase::Recovering)
        return FireballCastMotion::Recover(PoseSettings,Sample(RecoveryFromPhase,RecoveryFromFraction),Current,HandPhaseFraction());
    return Sample(HandPhase,HandPhaseFraction());
}
FVector UFPSFireballComponent::HeldOrbPosition() const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return GetOwner()->GetActorLocation();
    FVector Wrist=PoseSettings.GatherWrist;
    if(HandPhase==EFireballHandPhase::Raising && bHandEntryCaptured)
    {
        Wrist=FireballCastMotion::GatherWrist(PoseSettings,EntryHand.GetLocation(),GatherFraction());
    }
    // Once gathered the orb stays at its established hover offset, independently
    // of recovery, weapon handling and the later release gesture.
    const FVector HoldOffset=PoseSettings.PalmFrame(0).RotateVector(PoseSettings.OrbOffset);
    return Camera->GetComponentTransform().TransformPosition(Wrist+HoldOffset);
}
void UFPSFireballComponent::UpdateFallbackHands()
{
    if(!FallbackHands)return;
    bool OtherHandsVisible=false;
    TInlineComponentArray<UFPSCastingMeshComponent*> Meshes(GetOwner());
    for(const auto* Mesh:Meshes)if(Mesh!=FallbackHands && Mesh->GetSkeletalMeshAsset() && Mesh->IsVisible() && !Mesh->bHiddenInGame)
    { OtherHandsVisible=true;break; }
    const bool Show=IsOccupyingLeftHand() && !OtherHandsVisible;
    FallbackHands->SetVisibility(Show);
    if(Show){FallbackHands->TickAnimation(0.f,false);FallbackHands->RefreshBoneTransforms();}
}
float UFPSFireballComponent::HandPhaseFraction() const
{
    const float Duration=HandPhase==EFireballHandPhase::Raising?RaiseDuration:
        HandPhase==EFireballHandPhase::Releasing?ReleaseDuration:
        HandPhase==EFireballHandPhase::ReadyingRelease?ReleaseEntryDuration:RecoveryDuration;
    if(HandPhase==EFireballHandPhase::None)return 0.f;
    if(HandPhase==EFireballHandPhase::Holding)return 1.f;
    return FMath::Clamp(PhaseAge/FMath::Max(.01f,Duration),0.f,1.f);
}
float UFPSFireballComponent::GatherFraction() const
{ return HandPhase==EFireballHandPhase::Raising?HandPhaseFraction():1.f; }
void UFPSFireballComponent::Feedback(const FString& Text)
{ LastMessage=Text;MessageUntil=GetWorld()->GetTimeSeconds()+1.5; }
FString UFPSFireballComponent::StatusText() const
{
    if(bQueuedCast || (bQueuedLaunch && HandPhase==EFireballHandPhase::None))return TEXT("等待左手");
    if(GetWorld()&&GetWorld()->GetTimeSeconds()<MessageUntil)return LastMessage;
    if(HandPhase==EFireballHandPhase::Raising)return TEXT("凝聚");
    if(HandPhase==EFireballHandPhase::Releasing || HandPhase==EFireballHandPhase::ReadyingRelease)return TEXT("发射中");
    if(HandPhase==EFireballHandPhase::Recovering)return TEXT("收手");
    if(IsPrepared())return TEXT("发射");
    if(IsFlying())return TEXT("飞行");
    if(auto* P=Model();P&&P->FireballCooldown()>0)return FString::Printf(TEXT("%.1f"),P->FireballCooldown());
    return TEXT("");
}
float UFPSFireballComponent::CooldownFraction() const
{
    auto* P=Model();if(!P||Active.IsValid())return 0;
    const float Duration=LastCastCooldown>0?LastCastCooldown:P->FireballStats().Cooldown;
    return FMath::Clamp(P->FireballCooldown()/FMath::Max(.1f,Duration),0.f,1.f);
}
void UFPSFireballComponent::Trigger()
{
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>();Sword && Sword->IsGuarding())Sword->ReleaseGuard();
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* P=Model();
    if(!Player||!P||!Player->IsLocallyControlled()||GetWorld()->GetNetMode()!=NM_Standalone)return;
    if(auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H&&H->IsDead())return;
    if(IsFlying()||HandPhase==EFireballHandPhase::Releasing||HandPhase==EFireballHandPhase::ReadyingRelease)return;
    if(IsPrepared())
    {
        // A prepared orb is independent from the hand. Keep one release request,
        // including during gather recovery or an ongoing weapon/tool action.
        bQueuedLaunch=true;
        if(HandPhase==EFireballHandPhase::None)TryBeginQueuedLaunch();
        return;
    }
    if(IsOccupyingLeftHand())return;
    if(bQueuedCast)return;
    if(P->FireballCooldown()>0){Feedback(TEXT("冷却"));return;}
    if(!P->CanSpendMana(P->FireballStats().ManaCost)){Feedback(TEXT("缺蓝"));return;}
    if(!Core||!Trail||!Explosion||!Shockwave){Feedback(TEXT("缺素材"));return;}
    // Do not charge MP or interrupt an existing left-hand action while waiting.
    bQueuedCast=true;TryBeginQueuedCast();
}
void UFPSFireballComponent::TryBeginQueuedCast()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* P=Model();
    if(!bQueuedCast||!Player||!P||Player->IsLeftHandBusyForCast())return;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC||PC->IsLookInputIgnored()||PC->IsMoveInputIgnored())return;
    bQueuedCast=false;
    // The profile may have changed while a reload, swing or ADS was finishing.
    if(P->FireballCooldown()>0){Feedback(TEXT("冷却"));return;}
    if(!P->CanSpendMana(P->FireballStats().ManaCost)){Feedback(TEXT("缺蓝"));return;}
    auto* Camera=Player->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const FVector Eye=Camera->GetComponentLocation();FVector Position=AFPSFireballProjectile::HoverPosition(Player);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireballPrepare),false,Player);FHitResult Wall;
    if(GetWorld()->SweepSingleByChannel(Wall,Eye,Position,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(14),Query))Position=Wall.Location;
    if(FVector::Distance(Eye,Position)<35){Feedback(TEXT("受阻"));return;}
    FActorSpawnParameters Spawn;Spawn.Owner=Player;Spawn.Instigator=Player;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Ball=GetWorld()->SpawnActor<AFPSFireballProjectile>(Position,FRotator::ZeroRotator,Spawn);
    if(!Ball)return;
    const FFireballCast Snapshot=P->FireballStats();
    if(!P->BeginFireballCast()){Ball->Destroy();Feedback(TEXT("未施放"));return;}
    LastCastCooldown=Snapshot.Cooldown;
    Active=Ball;Ball->Prepare(this,Player,Snapshot,Core,Trail,Explosion,Shockwave,ImpactSound);
    bQueuedLaunch=bLaunchCommitted=false;SetHandPhase(EFireballHandPhase::Raising);
    LastMessage.Reset();MessageUntil=0;
}
void UFPSFireballComponent::TryBeginQueuedLaunch()
{
    if(!bQueuedLaunch || HandPhase!=EFireballHandPhase::None)return;
    if(!IsPrepared()){bQueuedLaunch=false;return;}
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player || Player->IsLeftHandBusyForCast())return;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC || PC->IsLookInputIgnored() || PC->IsMoveInputIgnored())return;
    // Capture the current weapon's hand pose again; it may have changed while
    // the detached orb was hovering. This does not reserve MP or spawn a new orb.
    bQueuedLaunch=false;bLaunchCommitted=false;
    SetHandPhase(EFireballHandPhase::ReadyingRelease);
    LastMessage.Reset();MessageUntil=0;
}
void UFPSFireballComponent::LaunchAtContact()
{
    if(bLaunchCommitted||!IsPrepared())return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    auto* Camera=Player?Player->FindComponentByClass<UCameraComponent>():nullptr;
    if(!Camera)return;
    const FVector Eye=Camera->GetComponentLocation(),End=Eye+Camera->GetForwardVector()*20000;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireballAim),true,Player);Query.AddIgnoredActor(Active.Get());
    FHitResult Aim;GetWorld()->LineTraceSingleByChannel(Aim,Eye,End,ECC_Visibility,Query);
    Active->Launch(Aim.bBlockingHit?Aim.ImpactPoint:End);
    bLaunchCommitted=true;bQueuedLaunch=false;
}
void UFPSFireballComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    // Also covers empty hands and traversal's short weapon-stow/retract gaps.
    ON_SCOPE_EXIT { UpdateFallbackHands(); };
    if(auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())
    { Cancel();return; }
    if(bQueuedCast){TryBeginQueuedCast();return;}
    if(HandPhase==EFireballHandPhase::None){TryBeginQueuedLaunch();return;}
    PhaseAge+=Delta;
    // Carry frame overshoot between phases so the timing is not frame-rate dependent.
    for(int32 Transition=0;Transition<3;++Transition)
    {
        if(HandPhase==EFireballHandPhase::Raising)
        {
            if(PhaseAge<RaiseDuration)return;
            const float Remainder=PhaseAge-FMath::Max(.01f,RaiseDuration);
            SetHandPhase(bQueuedLaunch?EFireballHandPhase::Releasing:EFireballHandPhase::Recovering);
            PhaseAge=FMath::Max(0.f,Remainder);
        }
        else if(HandPhase==EFireballHandPhase::ReadyingRelease)
        {
            if(PhaseAge<FMath::Max(.01f,ReleaseEntryDuration))return;
            const float Remainder=PhaseAge-FMath::Max(.01f,ReleaseEntryDuration);
            SetHandPhase(EFireballHandPhase::Releasing);PhaseAge=Remainder;
        }
        else if(HandPhase==EFireballHandPhase::Releasing)
        {
            if(PhaseAge>=FMath::Clamp(LaunchContactTime,0.f,FMath::Max(.01f,ReleaseDuration)))LaunchAtContact();
            if(PhaseAge<ReleaseDuration)return;
            const float Remainder=PhaseAge-FMath::Max(.01f,ReleaseDuration);
            SetHandPhase(EFireballHandPhase::Recovering);PhaseAge=FMath::Max(0.f,Remainder);
        }
        else if(HandPhase==EFireballHandPhase::Recovering)
        {
            if(PhaseAge>=FMath::Max(.01f,RecoveryDuration))SetHandPhase(EFireballHandPhase::None);
            return;
        }
        else return;
    }
}
void UFPSFireballComponent::ProjectileFinished(AFPSFireballProjectile* Projectile)
{
    if(Active.Get()!=Projectile)return;
    Active.Reset();bQueuedLaunch=false;
    // Expiry/cancellation while gathering also gives the hand a recovery phase.
    if(HandPhase==EFireballHandPhase::Raising || HandPhase==EFireballHandPhase::ReadyingRelease ||
       (HandPhase==EFireballHandPhase::Releasing && !bLaunchCommitted))SetHandPhase(EFireballHandPhase::Recovering);
    if(auto* P=Model())P->FinishFireballCast();
}
void UFPSFireballComponent::Cancel()
{
    bQueuedCast=bQueuedLaunch=bLaunchCommitted=false;
    if(Active.IsValid())Active->Destroy();Active.Reset();SetHandPhase(EFireballHandPhase::None);
    if(FallbackHands)FallbackHands->SetVisibility(false);
}
void UFPSFireballComponent::EndPlay(const EEndPlayReason::Type Reason)
{ Cancel();Super::EndPlay(Reason); }
