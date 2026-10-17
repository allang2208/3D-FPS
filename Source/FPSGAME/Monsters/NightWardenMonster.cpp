#include "NightWardenMonster.h"
#include "NightWardenAnimInstance.h"
#include "MonsterAIController.h"
#include "MonsterCharacterMovementComponent.h"
#include "MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

ANightWardenMonster::ANightWardenMonster(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<UMonsterCharacterMovementComponent>(CharacterMovementComponentName))
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates = true;
    SetReplicateMovement(true);
    Combat = CreateDefaultSubobject<UMonsterCombatComponent>(TEXT("CombatExecution"));
    AIControllerClass = AMonsterAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    bUseControllerRotationYaw = false;
    Tags.Add(TEXT("Enemy"));
    Tags.Add(TEXT("NightWarden"));

    // Share the existing Nurse navigation specification (34 / 184 / 40),
    // while preserving the V07 170 cm body and its ground offset.
    GetCapsuleComponent()->InitCapsuleSize(34.f, 85.f);
    auto* Movement = GetCharacterMovement();
    Movement->SetUpdateNavAgentWithOwnersCollisions(false);
    auto& Agent = Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius = 34.f; Agent.AgentHeight = 184.f; Agent.AgentStepHeight = 40.f;
    Movement->MaxWalkSpeed = WalkSpeed;
    Movement->MaxAcceleration = 180.f;
    Movement->BrakingDecelerationWalking = 240.f;
    Movement->GroundFriction = 2.f;
    Movement->bUseSeparateBrakingFriction = true;
    Movement->BrakingFriction = 1.f;
    Movement->GetNavMovementProperties()->bUseAccelerationForPaths = true;
    Movement->bOrientRotationToMovement = true;
    Movement->RotationRate = FRotator(0.f, 100.f, 0.f);
    Movement->bCanWalkOffLedges = false;

    auto* Body = GetMesh();
    Body->SetRelativeLocation(FVector(0, 0, -85.f));
    Body->SetRelativeRotation(FRotator::ZeroRotator);
    Body->SetAnimInstanceClass(UNightWardenAnimInstance::StaticClass());
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetCanEverAffectNavigation(false);
    Body->bEnableUpdateRateOptimizations = false;
    Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Body->bDisableClothSimulation = false;
    Body->ClothBlendWeight = 1.f;
    Body->SetTeleportDistanceThreshold(250.f);
    Body->SetTeleportRotationThreshold(100.f);
    Body->bResetAfterTeleport = true;
}

void ANightWardenMonster::BeginPlay()
{
    Home = GetActorLocation();
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
    GetMesh()->SetAnimInstanceClass(UNightWardenAnimInstance::StaticClass());
    Super::BeginPlay();
    if (GetNetMode() == NM_DedicatedServer)
    {
        GetMesh()->SuspendClothingSimulation();
        GetMesh()->ClothBlendWeight = 0.f;
    }
    else
    {
        GetMesh()->ResumeClothingSimulation();
        GetMesh()->ForceClothNextUpdateTeleportAndReset();
    }
}

void ANightWardenMonster::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (HasAuthority()) TickAttack(DeltaSeconds);
    if (GetNetMode() == NM_DedicatedServer) return;
    // Same distance hysteresis as WitchRebuilt. Idle/turn/move changes do not
    // reset the solver; the physical hem retains its inertia across transitions.
    double NearestSquared = TNumericLimits<double>::Max();
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        const auto* ViewerController = It->Get();
        if (ViewerController && ViewerController->IsLocalController())
            NearestSquared = FMath::Min(NearestSquared,
                FVector::DistSquared(ViewerController->GetFocalLocation(), GetActorLocation()));
    }
    if (NearestSquared < FMath::Square(2000.)) bWantsClothSimulation = true;
    else if (NearestSquared > FMath::Square(2400.)) bWantsClothSimulation = false;
    auto* Body = GetMesh();
    if (bWantsClothSimulation && Body->IsClothingSimulationSuspended())
    {
        Body->ResumeClothingSimulation();
        Body->ForceClothNextUpdateTeleportAndReset();
    }
    Body->ClothBlendWeight = FMath::FInterpConstantTo(Body->ClothBlendWeight,
        bWantsClothSimulation ? 1.f : 0.f, DeltaSeconds, 1.f / .35f);
    if (!bWantsClothSimulation && Body->ClothBlendWeight <= 0.f && !Body->IsClothingSimulationSuspended())
        Body->SuspendClothingSimulation();
}
