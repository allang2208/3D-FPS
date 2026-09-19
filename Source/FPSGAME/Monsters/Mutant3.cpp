#include "Mutant3.h"
#include "FatZombieAnimInstance.h"
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
    GetCapsuleComponent()->InitCapsuleSize(36.f, 85.f);
    Tags.Remove(TEXT("NurseZombie")); Tags.Add(TEXT("Mutant3"));
    MaxHealth = 750.f; AttackDamage = 40.f; WalkSpeed = 360.f;
    AttackRange = 130.f; ContactTime = .40f; ContactEnd = .51f;
    RecoveryTime = .65f; ExperienceReward = 482;
    GetCharacterMovement()->MaxAcceleration = 1100.f;
    GetCharacterMovement()->BrakingDecelerationWalking = 1400.f;
    GetCharacterMovement()->RotationRate = FRotator(0, 360, 0);
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Monsters/Mutant3Meshy/SK_Mutant3_Meshy.SK_Mutant3_Meshy"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Idle(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Idle.A_Mutant3_Idle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Walk(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Walking.A_Mutant3_Walking"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Run(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Running.A_Mutant3_Running"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Fast(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_RunFast.A_Mutant3_RunFast"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Attack(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Attack.A_Mutant3_Attack"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Death(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Death.A_Mutant3_Death"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Stagger(TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Stagger.A_Mutant3_Stagger"));
    static ConstructorHelpers::FClassFinder<AAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    VisualMesh = Model.Object; IdleClip = Idle.Object; WalkClip = Walk.Object;
    RunningClip = Run.Object; FastRunClip = Fast.Object; AttackClip = Attack.Object; DeathClip = Death.Object;
    Combat->HitClip = Stagger.Object;
    if (AI.Succeeded()) AIControllerClass = AI.Class;
    AlignVisual();
}

void AMutant3::BeginPlay()
{
    if (!Combat->HitClip)
        Combat->HitClip = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Monsters/Mutant3Meshy/Animations/A_Mutant3_Stagger.A_Mutant3_Stagger"));
    Super::BeginPlay();
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
    if (auto* Animation = GetBlendedAnimation())
        Animation->TransitionTo(Clip, bLoop, !bLoop, AnimationBlendSeconds);
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
        // Hysteresis keeps threshold crossings from restarting the transition.
        const float FastThreshold = Animation->ActiveClip == FastRunClip ? 280.f : 310.f;
        const float RunThreshold = Animation->ActiveClip == RunningClip ? 135.f : 170.f;
        UAnimSequence* Selected = WalkClip;
        float ReferenceSpeed = AnimationWalkSpeed;
        if (FastRunClip && Speed >= FastThreshold) { Selected = FastRunClip; ReferenceSpeed = AnimationFastRunSpeed; }
        else if (RunningClip && Speed >= RunThreshold) { Selected = RunningClip; ReferenceSpeed = AnimationRunSpeed; }
        if (Animation->ActiveClip != Selected)
            Animation->TransitionTo(Selected, true, false, AnimationBlendSeconds);
        Animation->SetLocomotionRate(FMath::Clamp(Speed / FMath::Max(1.f, ReferenceSpeed), .05f, 1.6f));
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
    if (auto* Animation = GetBlendedAnimation())
        Animation->BeginHitReaction(Clip, Combat->IsParryReaction() ? Combat->GetParryDirection() : IncomingHitDirection, Combat->IsParryReaction());
}

void AMutant3::SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining)
{
    const float ReactionElapsed = Combat->IsParryReaction() ? FMath::Max(0.f, Elapsed - .1f) : Elapsed;
    if (auto* Animation = GetBlendedAnimation()) Animation->SetHitReactionTime(ReactionElapsed, Remaining);
}

void AMutant3::StartDeathPresentation()
{
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
    Super::EndPlay(Reason);
}
