#include "FatZombie.h"
#include "FatZombieAnimInstance.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/DamageEvents.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/BodyInstance.h"
#include "UObject/ConstructorHelpers.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

AFatZombie::AFatZombie(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
    GetCapsuleComponent()->InitCapsuleSize(44.f, 86.f);
    Tags.Remove(TEXT("NurseZombie")); Tags.Add(TEXT("FatZombie"));
    // Development defaults; independently editable without changing the nurse.
    MaxHealth = 600.f; AttackDamage = 25.f; WalkSpeed = 65.f;
    AttackRange = 155.f; ContactTime = 1.f; ContactEnd = 1.18f;
    RecoveryTime = 1.f; CorpseSeconds = 15.f; ExperienceReward = 241;
    static ConstructorHelpers::FObjectFinder<USkeletalMesh> Model(TEXT("/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy.SK_FatZombie_Meshy"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Idle(TEXT("/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_Idle.A_FatZombie_Idle"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Walk(TEXT("/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_Walk.A_FatZombie_Walk"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Attack(TEXT("/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_Attack.A_FatZombie_Attack"));
    static ConstructorHelpers::FObjectFinder<UAnimSequence> Death(TEXT("/Game/Monsters/FatZombieMeshy/Animations/A_FatZombie_Death.A_FatZombie_Death"));
    static ConstructorHelpers::FClassFinder<AAIController> AI(TEXT("/Game/Monsters/AI/BP_MonsterAIController"));
    VisualMesh = Model.Object; IdleClip = Idle.Object; WalkClip = Walk.Object; AttackClip = Attack.Object; DeathClip = Death.Object;
    if (AI.Succeeded()) AIControllerClass = AI.Class;
    AlignVisual();
}

void AFatZombie::AlignVisual()
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

void AFatZombie::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    AlignVisual();
}

UFatZombieAnimInstance* AFatZombie::GetBlendedAnimation()
{
    if (!Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance()))
        GetMesh()->SetAnimInstanceClass(UFatZombieAnimInstance::StaticClass());
    return Cast<UFatZombieAnimInstance>(GetMesh()->GetAnimInstance());
}

void AFatZombie::StartStateAnimation(UAnimSequence* Clip, bool bLoop)
{
    if (auto* Animation = GetBlendedAnimation())
        Animation->TransitionTo(Clip, bLoop, !bLoop, AnimationBlendSeconds);
}

void AFatZombie::SetAttackAnimationTime(float Seconds)
{
    if (auto* Animation = GetBlendedAnimation()) Animation->SetCombatTime(Seconds);
}

void AFatZombie::SetWalkAnimationRate(float Rate)
{
    if (auto* Animation = GetBlendedAnimation())
        Animation->SetLocomotionRate(FMath::Clamp(GetVelocity().Size2D() / FMath::Max(1.f, AnimationWalkSpeed), 0.f, 2.f));
}

float AFatZombie::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    const bool WasAlive = State != ENurseState::Dead;
    IncomingHitDirection = -GetActorForwardVector();
    if (Event.IsOfType(FPointDamageEvent::ClassID))
        IncomingHitDirection = static_cast<const FPointDamageEvent&>(Event).ShotDirection;
    else if (Causer)
        IncomingHitDirection = GetActorLocation() - Causer->GetActorLocation();
    // The inherited damage entry owns health, interruption, death and rewards.
    const float Applied = Super::TakeDamage(Damage, Event, EventInstigator, Causer);
    if (WasAlive && State == ENurseState::Dead && bLeaveDeathPus)
    {
        DeathPusAnchor = FTransform(FRotator(0, GetActorRotation().Yaw, 0),
            GetActorLocation()-FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));
        // Visible residue starts with death; it does not wait for the animation
        // or the later ragdoll handoff. The alive-to-dead edge creates it once.
        SpawnDeathPus();
    }
    return Applied;
}

void AFatZombie::SpawnDeathPus()
{
    if (!HasAuthority() || State != ENurseState::Dead) return;
    if (auto* Pool = GetWorld()->SpawnActorDeferred<AFatZombiePusPool>(AFatZombiePusPool::StaticClass(),
        DeathPusAnchor, GetOwner(), this, ESpawnActorCollisionHandlingMethod::AlwaysSpawn))
    {
        Pool->InitializeFrom(this, DeathPus);
        UGameplayStatics::FinishSpawningActor(Pool, DeathPusAnchor);
    }
}

void AFatZombie::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DeathRagdollTimer);
    Super::EndPlay(Reason);
}

void AFatZombie::StartHitPresentation(UAnimSequence* Clip, float Duration)
{
    if (auto* Animation = GetBlendedAnimation())
        Animation->BeginHitReaction(IncomingHitDirection);
}

void AFatZombie::SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining)
{
    if (auto* Animation = GetBlendedAnimation()) Animation->SetHitReactionTime(Elapsed, Remaining);
}

void AFatZombie::StartDeathPresentation()
{
    GetMesh()->SetSimulatePhysics(false);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (DeathClip)
        if (auto* Animation = GetBlendedAnimation())
            Animation->TransitionTo(DeathClip, false, false, AnimationBlendSeconds);
    if (!bDeathRagdoll) return;
    // Play the complete authored fall before physics takes over the lying pose.
    const float Delay = FMath::Max(DeathClip ? DeathClip->GetPlayLength() : 0.f, RagdollDelay);
    if (Delay > 0.f) GetWorldTimerManager().SetTimer(DeathRagdollTimer, this, &ThisClass::StartDeathRagdoll, Delay, false);
    else StartDeathRagdoll();
}

void AFatZombie::StartDeathRagdoll()
{
    if (State != ENurseState::Dead || bRagdollActive) return;
    auto* BodyMesh = GetMesh();
    const auto* Physics = BodyMesh->GetPhysicsAsset();
    if (!Physics || Physics->FindBodyIndex(TEXT("FatZombieRoot")) == INDEX_NONE || Physics->ConstraintSetup.IsEmpty())
    {
        UE_LOG(LogTemp, Error, TEXT("FAT_RAGDOLL_ASSET_MISSING %s: install the prepared combat physics asset"), *GetName());
        return;
    }
    // Timers run independently of animation evaluation. Sample the exact last
    // frame before constructing physics bodies, even if the pose tick trails it.
    if (DeathClip)
        if (auto* Animation = GetBlendedAnimation())
        {
            Animation->FinishClip();
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
    // A non-contact root follows the pelvis and keeps the imported scaled root
    // aligned with physical bones; it must never act as a sphere on the floor.
    if (auto* Root = BodyMesh->GetBodyInstance(TEXT("FatZombieRoot")))
        Root->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BodyMesh->WakeAllRigidBodies();
    // The completed death animation already owns the fall. Do not kick the
    // settled corpse again; directional impulse is only a missing-clip fallback.
    if (!DeathClip)
        BodyMesh->AddImpulse(IncomingHitDirection.GetSafeNormal2D() * FMath::Clamp(RagdollImpulseSpeed, 0.f, 300.f), TEXT("Hips"), true);
    bRagdollActive = true;
    UE_LOG(LogTemp, Display, TEXT("FAT_RAGDOLL_STARTED %s bodies=%d constraints=%d"), *GetName(), Physics->SkeletalBodySetups.Num(), Physics->ConstraintSetup.Num());
}
