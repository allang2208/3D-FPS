#include "PlayerKnockdownComponent.h"
#include "PlayerKnockdownMotion.h"
#include "PlayerGuardBreakComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "FPSFurnitureRestComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"
#include "UObject/ObjectKey.h"

namespace PlayerKnockdownRuntime
{
double ServerNow(const UWorld* World)
{
    const auto* State=World?World->GetGameState():nullptr;
    return State?State->GetServerWorldTimeSeconds():(World?World->GetTimeSeconds():0.);
}
/** Owner -> component. Read every frame by the body animation, camera and first-person body: no component scans. */
TMap<TObjectKey<AActor>,TWeakObjectPtr<UPlayerKnockdownComponent>>& Registry()
{
    static TMap<TObjectKey<AActor>,TWeakObjectPtr<UPlayerKnockdownComponent>> Map;
    return Map;
}
}

UPlayerKnockdownComponent::UPlayerKnockdownComponent()
{
    SetIsReplicatedByDefault(true);
    // Only the server's wait for a landing ticks; everything else runs on timers and the readers' frames.
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
}

void UPlayerKnockdownComponent::OnRegister()
{
    Super::OnRegister();
    if(AActor* Owner=GetOwner())PlayerKnockdownRuntime::Registry().Add(Owner,this);
}

void UPlayerKnockdownComponent::OnUnregister()
{
    if(AActor* Owner=GetOwner())
        if(const auto* Found=PlayerKnockdownRuntime::Registry().Find(Owner);Found&&Found->Get()==this)
            PlayerKnockdownRuntime::Registry().Remove(Owner);
    Super::OnUnregister();
}

UPlayerKnockdownComponent* UPlayerKnockdownComponent::GetOrCreate(AActor* Owner)
{
    if(!Owner)return nullptr;
    if(auto* Found=Find(Owner))return Found;
    if(!Owner->HasAuthority())return nullptr;
    auto* Created=NewObject<UPlayerKnockdownComponent>(Owner);
    Owner->AddInstanceComponent(Created);Created->RegisterComponent();
    return Created;
}

UPlayerKnockdownComponent* UPlayerKnockdownComponent::Find(const AActor* Owner)
{
    if(!Owner)return nullptr;
    const auto* Found=PlayerKnockdownRuntime::Registry().Find(Owner);
    return Found?Found->Get():nullptr;
}

bool UPlayerKnockdownComponent::IsKnockedDown(const AActor* Owner)
{
    const auto* Found=Find(Owner);
    return Found&&Found->IsRunning();
}

bool UPlayerKnockdownComponent::HidesOwnerLowerBody(const AActor* Owner)
{
    const auto* Found=Find(Owner);
    return Found&&Found->IsRunning()&&!Found->HasFullBody();
}

bool UPlayerKnockdownComponent::GetDeathHoldView(const AActor* Owner,FVector& Eye,FRotator& Rotation)
{
    const auto* Found=Find(Owner);
    return Found&&Found->DeathHoldView(Eye,Rotation);
}

void UPlayerKnockdownComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    // Everyone receives the start: the world body of every observer plays the same clock.
    DOREPLIFETIME(UPlayerKnockdownComponent,StartedAt);
}

bool UPlayerKnockdownComponent::Apply()
{
    auto* Pawn=Cast<ACharacter>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||bActive||bPendingLanding||IsOwnerDead())return false;
    // Seated or lying on furniture the rest system owns body, camera and exit; it has no knockdown branch.
    if(UFPSFurnitureRestComponent::IsResting(Pawn))return false;
    const auto* Move=Pawn->GetCharacterMovement();
    // The clip lies on a floor; there is none to lie on in water or while flying.
    if(Move&&(Move->IsSwimming()||Move->IsFlying()))return false;
    if(Move&&Move->IsFalling())
    {
        bPendingLanding=true;PendingSince=GetWorld()->GetTimeSeconds();SetComponentTickEnabled(true);
        return true;
    }
    StartedAt=PlayerKnockdownRuntime::ServerNow(GetWorld());
    Pawn->ForceNetUpdate();
    Begin(0.f);
    return true;
}

void UPlayerKnockdownComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!bPendingLanding){SetComponentTickEnabled(false);return;}
    const auto* Pawn=Cast<ACharacter>(GetOwner());
    const auto* Move=Pawn?Pawn->GetCharacterMovement():nullptr;
    const bool bExpired=GetWorld()->GetTimeSeconds()-PendingSince>PlayerKnockdownMotion::LandingWait;
    if(!Move||IsOwnerDead()||bExpired||Move->IsSwimming()||Move->IsFlying())
    {bPendingLanding=false;SetComponentTickEnabled(false);return;}
    if(!Move->IsMovingOnGround())return;
    bPendingLanding=false;SetComponentTickEnabled(false);
    Apply();
}

void UPlayerKnockdownComponent::OnRep_StartedAt()
{
    if(StartedAt<0.||GetOwner()->HasAuthority())return;
    // A late or repeated receipt of a finished knockdown does nothing.
    const float Seconds=float(PlayerKnockdownRuntime::ServerNow(GetWorld())-StartedAt);
    if(Seconds<PlayerKnockdownMotion::Duration-.05f)Begin(FMath::Max(0.f,Seconds));
}

float UPlayerKnockdownComponent::Age() const
{
    return bActive?FMath::Clamp(float(GetWorld()->GetTimeSeconds()-LocalStartedAt),0.f,PlayerKnockdownMotion::Duration)
        :PlayerKnockdownMotion::Duration;
}

bool UPlayerKnockdownComponent::IsOwnerDead() const
{
    const UFPSCombatHealthComponent* Health=CachedHealth.Get();
    if(!Health&&GetOwner())Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    return Health&&Health->IsDead();
}

void UPlayerKnockdownComponent::UpdateDeathLatch() const
{
    if(bDeathLatched||!bActive||!IsOwnerDead())return;
    bDeathLatched=true;DeathAge=Age();DeathAt=GetWorld()->GetTimeSeconds();
}

float UPlayerKnockdownComponent::DeathHoldTime() const
{
    if(!bDeathLatched||DeathAge>=PlayerKnockdownMotion::DeathStandingFrom)return -1.f;
    const float Since=float(GetWorld()->GetTimeSeconds()-DeathAt);
    // Not yet settled: finish the fall onto the back. Already rising: sink back down at real speed.
    return DeathAge<=PlayerKnockdownMotion::DeathLieSeconds
        ?FMath::Min(DeathAge+Since,PlayerKnockdownMotion::DeathLieSeconds)
        :FMath::Max(PlayerKnockdownMotion::DeathLieSeconds,DeathAge-Since);
}

void UPlayerKnockdownComponent::BodyAnimationSample(float& Seconds,float& Weight) const
{
    UpdateDeathLatch();
    if(const float Hold=DeathHoldTime();Hold>=0.f){Seconds=Hold;Weight=1.f;return;}
    // Died (almost) upright: the standing death owns the body from here.
    if(!bActive||bDeathLatched)return;
    Seconds=Age();Weight=PlayerKnockdownMotion::BodyWeight(Seconds);
}

bool UPlayerKnockdownComponent::HasFullBody() const
{
    const UFPSPlayerBodyComponent* Body=CachedBody.Get();
    if(!Body&&GetOwner())Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    FVector Eye;
    // The eye track is only loaded when its recorded animation matches the active "Knockdown" clip.
    return Body&&Body->GetBodyMesh()&&Body->SampleFurnitureEye(PlayerKnockdownMotion::BodyClipRole,0.f,Eye);
}

bool UPlayerKnockdownComponent::DeathHoldView(FVector& Eye,FRotator& Rotation) const
{
    UpdateDeathLatch();
    const float T=DeathHoldTime();
    if(T<0.f||!bHasLastView)return false;
    const UFPSPlayerBodyComponent* Body=CachedBody.Get();
    FVector EyeInMesh;
    Eye=Body&&Body->GetBodyMesh()&&Body->SampleFurnitureEye(PlayerKnockdownMotion::BodyClipRole,T,EyeInMesh)
        ?Body->GetBodyMesh()->GetComponentTransform().TransformPosition(EyeInMesh):LastEye;
    const auto S=PlayerKnockdownMotion::Camera(T,LastBaseEyeCm,LastBasePitch);
    Rotation=FRotator(S.Pitch,LastYaw+S.YawAdd,LastRoll+S.Roll);
    return true;
}

void UPlayerKnockdownComponent::Begin(float InitialAge)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn)return;
    CachedHealth=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    CachedBody=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();
    bActive=true;bDeathLatched=false;LocalStartedAt=GetWorld()->GetTimeSeconds()-InitialAge;
    // The clip stands up at full height: leave a crouch on the machines that simulate this character's movement.
    if((Pawn->HasAuthority()||Pawn->IsLocallyControlled())&&Pawn->bIsCrouched)Pawn->UnCrouch();
    // Same lock as the guard-break stun: no movement, look or action input until the character stands.
    if(auto* PC=Cast<APlayerController>(Pawn->GetController()))
    {
        // Every weapon family: the shared priority interrupt cancels swings, draws, casts, tool use, reloads,
        // dodge, slide and traversal. Only the owning machine may sync/re-apply the profile (`false`): that path
        // reads the game instance's local status model, which on a listen server is the HOST's profile. The
        // server's copy of a remote player cancels without touching any profile, like death does (`true`).
        // The menu suspension (aim previews, pending spells) is owner-local presentation.
        if(Pawn->IsLocallyControlled())
        {
            Pawn->InterruptActionsForPriority(false);
            Pawn->SuspendWeaponForMenu();
        }
        else Pawn->InterruptActionsForPriority(true);
        Pawn->StopJumping();Pawn->ConsumeMovementInputVector();
        if(auto* Move=Pawn->GetCharacterMovement())Move->StopMovementImmediately();
        if(!LockedController.IsValid())
        {
            LockedController=PC;PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);Pawn->DisableInput(PC);
        }
    }
    if(Pawn->IsLocallyControlled())
    {
        if(auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>())Sword->PresentKnockdown(InitialAge);
        BeginViewmodelDrop();
    }
    GetWorld()->GetTimerManager().SetTimer(Timer,this,&UPlayerKnockdownComponent::Release,
        FMath::Max(.01f,PlayerKnockdownMotion::Duration-InitialAge),false);
    UE_LOG(LogTemp,Display,TEXT("KNOCKDOWN begin %s age=%.3f local=%d fullbody=%d"),*Pawn->GetName(),InitialAge,
        Pawn->IsLocallyControlled()?1:0,HasFullBody()?1:0);
}

void UPlayerKnockdownComponent::Release()
{
    // A death during the knockdown must be latched before the running flag drops (it decides the death hold).
    UpdateDeathLatch();
    if(UWorld* World=GetWorld())World->GetTimerManager().ClearTimer(Timer);
    bActive=false;
    EndViewmodelDrop();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(auto* PC=LockedController.Get())
    {
        // Move/look ignores are counted; the key bindings are not. A guard-break stun that is still running owns
        // them until its own release.
        PC->SetIgnoreMoveInput(false);PC->SetIgnoreLookInput(false);
        const auto* Stun=Pawn?Pawn->FindComponentByClass<UPlayerGuardBreakComponent>():nullptr;
        if(Pawn&&!Pawn->IsActorBeingDestroyed()&&!IsOwnerDead()&&!(Stun&&Stun->IsActive()))Pawn->EnableInput(PC);
    }
    LockedController.Reset();
}

void UPlayerKnockdownComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    bPendingLanding=false;
    Release();Super::EndPlay(Reason);
}

void UPlayerKnockdownComponent::RestoreCamera(UCameraComponent& Camera)
{
    if(!bCameraApplied)return;
    bCameraApplied=false;
    Camera.SetRelativeLocation(CameraBaseRelative);
}

void UPlayerKnockdownComponent::ApplyCamera(UCameraComponent& Camera)
{
    if(!bActive)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||!Pawn->GetCapsuleComponent())return;
    const float T=Age();
    if(ViewmodelDropRoot&&!DroppedViewmodels.IsEmpty())ViewmodelDropRoot->SetRelativeTransform(PlayerKnockdownMotion::ViewmodelDrop(T));
    const UFPSPlayerBodyComponent* Body=CachedBody.Get();
    const FVector Base=Camera.GetComponentLocation();
    const FRotator View=Camera.GetComponentRotation();
    const float FloorZ=Pawn->GetActorLocation().Z-Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    // A death stops the character's tick (and this call); the death camera continues from these.
    LastEye=Base;LastBaseEyeCm=Base.Z-FloorZ;LastBasePitch=FRotator::NormalizeAxis(View.Pitch);
    LastYaw=View.Yaw;LastRoll=View.Roll;bHasLastView=true;
    // The observation camera keeps its own view of the falling body; only the first-person eye falls.
    if(Body&&Body->IsThirdPersonViewEnabled())return;
    const auto S=PlayerKnockdownMotion::Camera(T,Base.Z-FloorZ,FRotator::NormalizeAxis(View.Pitch));
    FVector Desired;
    FVector EyeInMesh;
    if(Body&&Body->GetBodyMesh()&&Body->SampleFurnitureEye(PlayerKnockdownMotion::BodyClipRole,T,EyeInMesh))
    {
        // Position follows the world body's authored head (it lands where the body really lies); rotation keeps
        // the bounded first-person curve instead of every head-bone turn.
        const FVector Head=Body->GetBodyMesh()->GetComponentTransform().TransformPosition(EyeInMesh);
        Desired=FMath::Lerp(Base,Head,PlayerKnockdownMotion::EyeTrackWeight(T));
    }
    else
    {
        Desired=Base+FRotator(0.f,View.Yaw,0.f).RotateVector(FVector(S.BackCm,S.SideCm,0.f));
        Desired.Z=FloorZ+S.EyeHeightCm;
    }
    UWorld* World=GetWorld();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PlayerKnockdownCamera),false,Pawn);
    FHitResult Floor;
    if(World->LineTraceSingleByChannel(Floor,Desired+FVector(0.f,0.f,30.f),Desired-FVector(0.f,0.f,80.f),ECC_Camera,Query)
        &&Floor.ImpactNormal.Z>.3f)
        Desired.Z=FMath::Max(Desired.Z,Floor.ImpactPoint.Z+PlayerKnockdownMotion::MinFloorClearanceCm);
    // Swept from inside the capsule: a wall or prop behind the player stops the head instead of the view.
    const FVector Pivot=Pawn->GetActorLocation();
    FHitResult Hit;
    if(World->SweepSingleByChannel(Hit,Pivot,Desired,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(10.f),Query))
        Desired=Hit.bStartPenetrating?Pivot:Hit.Location;
    CameraBaseRelative=Camera.GetRelativeLocation();bCameraApplied=true;
    Camera.SetWorldLocation(Desired);
    Camera.SetWorldRotation(FRotator(S.Pitch,View.Yaw+S.YawAdd,View.Roll+S.Roll));
    LastEye=Desired;
}

void UPlayerKnockdownComponent::BeginViewmodelDrop()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    UCameraComponent* Camera=Pawn?Pawn->FirstPersonCamera.Get():nullptr;
    if(!Camera||!DroppedViewmodels.IsEmpty())return;
    // A weapon with its own knockdown clip keeps it: the camera child that carries the sword arms stays.
    const USceneComponent* Keep=nullptr;
    if(const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsEquipped())
        for(const USceneComponent* Node=Sword->ArmsMesh();Node;Node=Node->GetAttachParent())
            if(Node->GetAttachParent()==Camera){Keep=Node;break;}
    if(!ViewmodelDropRoot)
    {
        ViewmodelDropRoot=NewObject<USceneComponent>(Pawn,TEXT("KnockdownViewmodelDrop"),RF_Transient);
        ViewmodelDropRoot->SetupAttachment(Camera);ViewmodelDropRoot->RegisterComponent();
    }
    ViewmodelDropRoot->SetRelativeTransform(FTransform::Identity);
    TArray<USceneComponent*> Children;Camera->GetChildrenComponents(false,Children);
    for(USceneComponent* Child:Children)
    {
        if(!Child||Child==ViewmodelDropRoot||Child==Keep)continue;
        // Only first-person presentation: owner-only primitives somewhere below this child.
        bool bViewmodel=false;
        TArray<USceneComponent*> Subtree;Child->GetChildrenComponents(true,Subtree);Subtree.Add(Child);
        for(const USceneComponent* Node:Subtree)
            if(const auto* Primitive=Cast<UPrimitiveComponent>(Node);Primitive&&Primitive->bOnlyOwnerSee){bViewmodel=true;break;}
        if(!bViewmodel)continue;
        // Keep the relative transform: each weapon still animates its own component, now inside the drop root.
        Child->AttachToComponent(ViewmodelDropRoot,FAttachmentTransformRules::KeepRelativeTransform);
        DroppedViewmodels.Add(Child);
    }
}

void UPlayerKnockdownComponent::EndViewmodelDrop()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    UCameraComponent* Camera=Pawn?Pawn->FirstPersonCamera.Get():nullptr;
    if(ViewmodelDropRoot)ViewmodelDropRoot->SetRelativeTransform(FTransform::Identity);
    for(const auto& Weak:DroppedViewmodels)
        if(USceneComponent* Child=Weak.Get();Child&&Camera&&Child->GetAttachParent()==ViewmodelDropRoot)
            Child->AttachToComponent(Camera,FAttachmentTransformRules::KeepRelativeTransform);
    DroppedViewmodels.Reset();
}

void AFPSGAMECharacter::KnockdownTestPressed()
{
#if !UE_BUILD_SHIPPING
    if(!IsLocallyControlled())return;
    UE_LOG(LogTemp,Display,TEXT("KNOCKDOWN test key Y (two-handed sword=%d)"),RuneSword&&RuneSword->IsEquipped()?1:0);
    ServerTestKnockdown();
#endif
}

void AFPSGAMECharacter::ServerTestKnockdown_Implementation()
{
    // Development entry only: a shipping server ignores it, so no client can knock itself down on demand.
#if !UE_BUILD_SHIPPING
    // The test key stands in for a blow from straight ahead: fall backwards.
    if(auto* Knockdown=UPlayerKnockdownComponent::GetOrCreate(this))Knockdown->Apply();
#endif
}
