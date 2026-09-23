#include "Mutant3.h"
#include "FatZombieAnimInstance.h"
#include "Mutant3GaitPhases.inl"
#include "MonsterCombatComponent.h"
#include "MonsterCombatTuning.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/DamageEvents.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/BodyInstance.h"
#include "UObject/ConstructorHelpers.h"
#include "TimerManager.h"

AMutant3::AMutant3(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
    GetCapsuleComponent()->InitCapsuleSize(34.f, 85.f);
    ConfigureFeralNavigation();
    Tags.Remove(TEXT("NurseZombie")); Tags.Add(TEXT("Mutant3"));
    MaxHealth = 750.f; AttackDamage = 40.f; WalkSpeed = 560.f;
    AttackRange = 150.f; ContactTime = .13f; ContactEnd = .25f;
    RecoveryTime = .65f; ExperienceReward = 482;
    GetCharacterMovement()->MaxAcceleration = 1800.f;
    GetCharacterMovement()->BrakingDecelerationWalking = 1800.f;
    GetCharacterMovement()->RotationRate = FRotator(0, 540, 0);
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw.SK_Mutant3_Claw"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Idle(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_FeralIdle.A_Mutant3_FeralIdle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Run(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_FeralRun.A_Mutant3_FeralRun"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Fast(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_FeralSprint.A_Mutant3_FeralSprint"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Attack(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_ClawA.A_Mutant3_ClawA"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> ClawB(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_ClawB.A_Mutant3_ClawB"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> ClawC(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_ClawC.A_Mutant3_ClawC"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Windup(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_PounceWindup.A_Mutant3_PounceWindup"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Flight(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_PounceFlight.A_Mutant3_PounceFlight"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Land(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations/A_Mutant3_PounceLand.A_Mutant3_PounceLand"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Death(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Death.A_Mutant3_Death"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Stagger(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Stagger.A_Mutant3_Stagger"));
    static ConstructorHelpers::FClassFinder<AAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    VisualMesh = Model.Object; IdleClip = Idle.Object; WalkClip = Run.Object;
    RunningClip = Run.Object; FastRunClip = Fast.Object; AttackClip = Attack.Object; DeathClip = Death.Object;
    ClawClips = {Attack.Object, ClawB.Object, ClawC.Object};
    PounceWindupClip = Windup.Object; PounceFlightClip = Flight.Object; PounceLandClip = Land.Object;
    Combat->HitClip = Stagger.Object;
    if (AI.Succeeded()) AIControllerClass = AI.Class;
    AlignVisual();
}

void AMutant3::BeginPlay()
{
    ConfigureFeralNavigation();
    if (!Combat->HitClip)
        Combat->HitClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Stagger.A_Mutant3_Stagger"));
    Super::BeginPlay();
    OnCharacterMovementUpdated.AddDynamic(this, &ThisClass::UpdateFeralFloorOffset);
    InitializeSurfaceStreaming();
}

void AMutant3::ConfigureFeralNavigation()
{
    // Fit the existing Nurse navmesh physically, rather than selecting the
    // 62 cm HandBrain agent for a 36 cm capsule. Keep the 170 cm body height.
    GetCapsuleComponent()->SetCapsuleRadius(34.f);
    auto* Move = GetCharacterMovement();
    Move->SetUpdateNavAgentWithOwnersCollisions(false);
    auto& Agent = Move->GetNavAgentPropertiesRef();
    Agent.AgentRadius = 34.f;
    Agent.AgentHeight = 184.f;
    Agent.AgentStepHeight = 40.f;
}

void AMutant3::UpdateFeralFloorOffset(float DeltaSeconds, FVector OldLocation, FVector OldVelocity)
{
    auto* BodyMesh = GetMesh();
    auto* Move = GetCharacterMovement();
    if (State == ENurseState::Dead || BodyMesh->IsSimulatingPhysics() || BodyMesh->GetAttachParent() != GetCapsuleComponent() ||
        GetLocalRole() == ROLE_SimulatedProxy) return;
    // UE keeps a small collision clearance above its supporting floor. The
    // authored sole is at 0.3 cm, so remove only that native clearance from the
    // visual mesh. Delta application preserves the shared stair smoothing offset.
    const float Gap = Move->IsMovingOnGround() && Move->CurrentFloor.IsWalkableFloor()
        ? FMath::Max(0.f, Move->CurrentFloor.GetDistanceToFloor()) : 0.f;
    const FVector Offset = GetCapsuleComponent()->GetComponentTransform().InverseTransformVector(FVector(0,0,-Gap));
    BodyMesh->SetRelativeLocation(BodyMesh->GetRelativeLocation()-AppliedFeralFloorOffset+Offset);
    AppliedFeralFloorOffset = Offset;
}

void AMutant3::AlignVisual()
{
    if (!VisualMesh) return;
    GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    const auto& Skeleton = VisualMesh->GetRefSkeleton();
    const int32 Head = Skeleton.FindBoneIndex(TEXT("Head"));
    const int32 Front = Skeleton.FindBoneIndex(TEXT("headfront"));
    if (Head != INDEX_NONE && Front != INDEX_NONE)
    {
        auto Position = [&Skeleton](int32 Bone)
        {
            FTransform Transform = Skeleton.GetRefBonePose()[Bone];
            for (int32 Parent = Skeleton.GetParentIndex(Bone); Parent != INDEX_NONE; Parent = Skeleton.GetParentIndex(Parent))
                Transform = Transform * Skeleton.GetRefBonePose()[Parent];
            return Transform.GetLocation();
        };
        const FVector Forward = (Position(Front) - Position(Head)).GetSafeNormal2D();
        if (!Forward.IsNearlyZero()) GetMesh()->SetRelativeRotation(FRotator(0, -Forward.Rotation().Yaw, 0));
    }
    const auto Bounds = VisualMesh->GetBounds();
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() - (Bounds.Origin.Z - Bounds.BoxExtent.Z)));
    AppliedFeralFloorOffset = FVector::ZeroVector;
}

void AMutant3::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    AlignVisual();
}

UFatZombieAnimInstance* AMutant3::GetBlendedAnimation()
{
    if (!Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
    return Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance());
}

void AMutant3::StartStateAnimation(UAnimSequence* Clip, bool bLoop)
{
    if (bLoop)
    {
        if (State == ENurseState::Chase) SetWalkAnimationRate(1.f);
        else TransitionFeralLocomotion(Clip, 1.f, .24f);
        return;
    }
    if (auto* Animation = GetBlendedAnimation())
        Animation->TransitionTo(Clip, bLoop, !bLoop, AnimationBlendSeconds);
}

void AMutant3::TransitionFeralLocomotion(UAnimSequence* Clip, float PlayRate, float BlendSeconds)
{
    auto* Animation = GetBlendedAnimation();
    if (!Animation || !Clip) return;
    if (Animation->ActiveClip == Clip && Animation->bLooping)
    {
        // Recovery already plays idle. A state-only change must not restart
        // its pose snapshot, gait phase, or playback-rate interpolation.
        Animation->SetLocomotionRate(PlayRate);
        return;
    }
    FMonsterClipTransition Settings;
    Settings.InitialPlayRate = PlayRate;
    Settings.bContinueOutgoingLoop = true;
    const UAnimSequence* Previous = Animation->ActiveClip;
    // V2 run contains three strides, sprint contains two. Normalizing by the
    // whole clip duration does not align feet; use their sampled gait map.
    if (Previous && Previous->GetPathName().StartsWith(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/")) &&
        Clip->GetPathName().StartsWith(TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/")))
    {
        if (Previous == RunningClip && Clip == FastRunClip)
        {
            const int32 Frame = FMath::RoundToInt(Animation->ClipTime*60.f) % UE_ARRAY_COUNT(Mutant3GaitPhases::RunToSprint);
            Settings.StartTime = Mutant3GaitPhases::RunToSprint[Frame]/60.f;
        }
        else if (Previous == FastRunClip && Clip == RunningClip)
        {
            const int32 Frame = FMath::RoundToInt(Animation->ClipTime*60.f) % UE_ARRAY_COUNT(Mutant3GaitPhases::SprintToRun);
            Settings.StartTime = Mutant3GaitPhases::SprintToRun[Frame]/60.f;
        }
    }
    Animation->TransitionTo(Clip, true, false, BlendSeconds, Settings);
}

void AMutant3::SetAttackAnimationTime(float Seconds)
{
    if (auto* Animation = GetBlendedAnimation()) Animation->SetCombatTime(Seconds);
}

void AMutant3::SetWalkAnimationRate(float Rate)
{
    if (auto* Animation = GetBlendedAnimation())
    {
        const float Speed = GetVelocity().Size2D();
        // Chase is an AI intent, not proof of movement. Blocked/arrived actors
        // idle at normal speed instead of playing the run at 5% speed.
        const float IdleThreshold = Animation->ActiveClip == IdleClip ? 65.f : 35.f;
        if (IdleClip && Speed < IdleThreshold)
        {
            TransitionFeralLocomotion(IdleClip, 1.f, AnimationBlendSeconds);
            return;
        }
        // Hysteresis keeps threshold crossings from restarting the transition.
        const float FastThreshold = Animation->ActiveClip == FastRunClip ? 420.f : 460.f;
        const float RunThreshold = Animation->ActiveClip == RunningClip ? 135.f : 170.f;
        UAnimSequence* Selected = WalkClip;
        float ReferenceSpeed = AnimationWalkSpeed;
        if (FastRunClip && Speed >= FastThreshold) { Selected = FastRunClip; ReferenceSpeed = AnimationFastRunSpeed; }
        else if (RunningClip && Speed >= RunThreshold) { Selected = RunningClip; ReferenceSpeed = AnimationRunSpeed; }
        TransitionFeralLocomotion(Selected,
            FMath::Clamp(Speed / FMath::Max(1.f, ReferenceSpeed), .35f, 1.6f), AnimationBlendSeconds);
    }
}

float AMutant3::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    IncomingHitDirection = -GetActorForwardVector();
    if (Event.IsOfType(FPointDamageEvent::ClassID)) IncomingHitDirection = static_cast<const FPointDamageEvent&>(Event).ShotDirection;
    else if (Causer) IncomingHitDirection = GetActorLocation() - Causer->GetActorLocation();
    return Super::TakeDamage(Damage, Event, EventInstigator, Causer);
}

void AMutant3::StartHitPresentation(UAnimSequence* Clip, float Duration)
{
    CancelFeralAction();
    if (auto* Animation = GetBlendedAnimation())
        Animation->BeginHitReaction(Clip, Combat->IsParryReaction() ? Combat->GetParryDirection() : IncomingHitDirection, Combat->IsParryReaction(), .07f);
}

void AMutant3::SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining)
{
    const float ReactionElapsed = Combat->IsParryReaction() ? FMath::Max(0.f, Elapsed - .1f) : Elapsed;
    if (auto* Animation = GetBlendedAnimation()) Animation->SetHitReactionTime(ReactionElapsed, Remaining);
}

void AMutant3::StartDeathPresentation()
{
    CancelFeralAction();
    GetMesh()->SetSimulatePhysics(false);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (DeathClip)
        if (auto* Animation = GetBlendedAnimation()) Animation->TransitionTo(DeathClip, false, false, AnimationBlendSeconds);
    if (!bDeathRagdoll) return;
    const float Delay = DeathClip ? DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction : 0.f;
    if (Delay > 0.f) GetWorldTimerManager().SetTimer(DeathRagdollTimer, this, &ThisClass::StartDeathRagdoll, Delay, false);
    else StartDeathRagdoll();
}

void AMutant3::StartDeathRagdoll()
{
    if (State != ENurseState::Dead || bRagdollActive) return;
    auto* BodyMesh = GetMesh();
    const auto* Physics = BodyMesh->GetPhysicsAsset();
    if (!Physics || Physics->FindBodyIndex(TEXT("Mutant3Root")) == INDEX_NONE || Physics->ConstraintSetup.IsEmpty())
    {
        UE_LOG(LogTemp, Error, TEXT("MUTANT3_RAGDOLL_ASSET_MISSING %s"), *GetName());
        return;
    }
    if (DeathClip)
        if (auto* Animation = GetBlendedAnimation())
        {
            Animation->HoldClipAtTime(DeathClip->GetPlayLength() * MonsterCombatTuning::DeathAnimationFraction);
            BodyMesh->TickAnimation(0.f, false);
        }
    BodyMesh->RefreshBoneTransforms();
    BodyMesh->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    BodyMesh->SetCollisionProfileName(TEXT("Ragdoll"));
    BodyMesh->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
    BodyMesh->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    BodyMesh->bPauseAnims = true;
    BodyMesh->KinematicBonesUpdateType = EKinematicBonesUpdateToPhysics::SkipAllBones;
    BodyMesh->SetAllBodiesSimulatePhysics(true);
    BodyMesh->SetSimulatePhysics(true);
    BodyMesh->SetAllPhysicsLinearVelocity(FVector::ZeroVector);
    BodyMesh->SetAllPhysicsAngularVelocityInRadians(FVector::ZeroVector);
    if (auto* Root = BodyMesh->GetBodyInstance(TEXT("Mutant3Root"))) Root->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BodyMesh->WakeAllRigidBodies();
    if (!DeathClip) BodyMesh->AddImpulse(IncomingHitDirection.GetSafeNormal2D()*90.f, TEXT("Hips"), true);
    bRagdollActive = true;
}

void AMutant3::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DeathRagdollTimer);
    GetWorldTimerManager().ClearTimer(SurfaceStreamingTimer);
    // The same four textures are shared by nearby mutants. Let our short
    // request expire rather than cancel another instance's residency request.
    SurfaceStreamingTextures.Reset();
    Super::EndPlay(Reason);
}
