#include "VortexCofferM25.h"
#include "MonsterCorpseRagdollComponent.h"
#include "M25AnimInstance.h"
#include "M25BackElectricComponent.h"
#include "M25MagicComponent.h"
#include "M25BiteComponent.h"
#include "MonsterAIController.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

AVortexCofferM25::AVortexCofferM25(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(CharacterMovementComponentName)
        .SetDefaultSubobjectClass<UMonsterIdleBreathingMeshComponent>(MeshComponentName))
{
    // Shared BT pursuit also uses this as the actor's enabled/disabled gate.
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    Combat = CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    CorpseRagdoll = CreateDefaultSubobject<UMonsterCorpseRagdollComponent>(TEXT("CorpseRagdoll"));
    CorpseRagdoll->Rig = EMonsterCorpseRig::Mawcrawler;
    BackElectric = CreateDefaultSubobject<UM25BackElectricComponent>(TEXT("BackElectric"));
    Magic = CreateDefaultSubobject<UM25MagicComponent>(TEXT("MagicExecution"));
    Bite = CreateDefaultSubobject<UM25BiteComponent>(TEXT("BiteExecution"));
    GetCapsuleComponent()->InitCapsuleSize(225.f, 225.f);
    GetMesh()->SetRelativeLocation(FVector(0, 0, -225.f));
    ApplyHitCollision();
    GetMesh()->SetGenerateOverlapEvents(false);
    GetMesh()->SetCanEverAffectNavigation(false);
    GetMesh()->SetAnimInstanceClass(UM25AnimInstance::StaticClass());
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetMesh()->bEnableUpdateRateOptimizations = true;

    auto* Movement = GetCharacterMovement();
    Movement->MaxWalkSpeed = WalkSpeed;
    Movement->MaxAcceleration = 90.f;
    Movement->BrakingDecelerationWalking = 120.f;
    Movement->RotationRate = FRotator(0, 55.f, 0);
    Movement->bOrientRotationToMovement = true;
    Movement->bCanWalkOffLedges = false;
    Movement->bRunPhysicsWithNoController = true;
    Movement->MaxStepHeight = 30.f;
    // Reuse the installed M10 large-body navigation agent.
    Movement->GetNavAgentPropertiesRef().AgentRadius = 225.f;
    Movement->GetNavAgentPropertiesRef().AgentHeight = 450.f;
    Movement->GetNavAgentPropertiesRef().AgentStepHeight = 30.f;
    bUseControllerRotationYaw = false;
    BaseEyeHeight = -180.f;
    AIControllerClass = AMonsterAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    SetCanBeDamaged(true);
    Tags.Add(TEXT("Enemy"));
    Tags.Add(TEXT("VortexCofferM25"));
}

void AVortexCofferM25::GetActorEyesViewPoint(FVector& Location, FRotator& Rotation) const
{
    // Sight originates near the exposed electrodes instead of the low capsule eye.
    Location = Magic ? Magic->ElectrodeLocation() + FVector(0, 0, 10.f) : GetActorLocation();
    Rotation = GetActorRotation();
}

void AVortexCofferM25::ApplyVisual()
{
    if (!VisualMesh) return;
    if (GetMesh()->GetSkeletalMeshAsset() != VisualMesh)
        GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    if (HitSurfacePhysics && GetMesh()->GetPhysicsAsset() != HitSurfacePhysics)
        GetMesh()->SetPhysicsAsset(HitSurfacePhysics);
    const FBoxSphereBounds Bounds = VisualMesh->GetBounds();
    const float Bottom = Bounds.Origin.Z - Bounds.BoxExtent.Z;
    GetMesh()->SetRelativeLocation(FVector(0, 0, -GetCapsuleComponent()->GetUnscaledCapsuleHalfHeight() - Bottom));
    GetMesh()->SetRelativeRotation(FRotator(0, MeshYaw, 0));
}

void AVortexCofferM25::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    ApplyVisual();
    ApplyHitCollision();
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
}

void AVortexCofferM25::BeginPlay()
{
    Super::BeginPlay();
    ApplyVisual();
    ApplyHitCollision();
    SetCanBeDamaged(true);
    if (HasAuthority())
    {
        MaxHealth = FMath::Max(1.f, MaxHealth * float(MonsterCoreStats::HealthMultiplier()));
        Health = MaxHealth;
    }
    Home = GetActorLocation();
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
    GetMesh()->AddTickPrerequisiteComponent(GetCharacterMovement());
    if (auto* AI = Cast<AMonsterAIController>(GetController()))
        AI->UpdateKnowledge();
}

bool AVortexCofferM25::CanAttackTarget(APawn* Target) const
{
    return !Dead() && !Controlled() && ((Bite && Bite->CanAttack(Target)) || (Magic && Magic->CanAttack(Target)));
}

bool AVortexCofferM25::AttackBusy() const
{
    const bool Executing = (Bite && Bite->IsBusy()) || (Magic && Magic->IsBusy());
    // Hold movement only when no other channel can start. Selection still belongs to the shared BT.
    return Executing && !CanAttackTarget(CombatTarget.Get());
}

bool AVortexCofferM25::StartAttack(APawn* Target)
{
    if (Dead() || Controlled()) return false;
    if (Bite && Bite->CanAttack(Target)) return Bite->StartAttack(Target);
    return Magic && Magic->StartAttack(Target);
}

void AVortexCofferM25::SetCombatTarget(APawn* Target)
{
    if (Target) bHasSearchGoal = false;
    CombatTarget = Target;
    if (Bite) Bite->SetTarget(Target);
    if (Magic) Magic->SetTarget(Target);
}

void AVortexCofferM25::RefreshCombatPoseTick()
{
    const bool Executing = !Dead() && (Controlled() || (Bite && Bite->IsBusy()) || (Magic && Magic->IsBusy()));
    auto* Body = GetMesh();
    if (Executing && !bCombatPoseOverride)
    {
        bCombatPoseOverride = true;
        SavedPoseTick = uint8(Body->VisibilityBasedAnimTickOption);
        bSavedUpdateRateOptimization = Body->bEnableUpdateRateOptimizations;
        Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Body->bEnableUpdateRateOptimizations = false;
    }
    else if (!Executing && bCombatPoseOverride)
    {
        Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption(SavedPoseTick);
        Body->bEnableUpdateRateOptimizations = bSavedUpdateRateOptimization;
        bCombatPoseOverride = false;
    }
}
