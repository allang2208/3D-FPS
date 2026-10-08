#include "MonsterCharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"

UMonsterCharacterMovementComponent::UMonsterCharacterMovementComponent()
{
    MaxStepHeight = 40.f;
    StairVisualSpeed = 160.f;
    // Use native planar support sweeps for stairs. The tread-height check below
    // also guards early corner perching by broad capsules.
    bUseFlatBaseForFloorChecks = true;
    GetNavAgentPropertiesRef().AgentStepHeight = MaxStepHeight;
}

bool UMonsterCharacterMovementComponent::IsWalkable(const FHitResult& Hit) const
{
    if (!Super::IsWalkable(Hit)) return false;
    // Do not let a broad capsule's rounded edge treat a higher flat tread as a ramp.
    // The reference predates FindFloor, which mutates CurrentFloor while testing.
    return !(IsMovingOnGround() && bHaveFrameFloor && Hit.ImpactNormal.Z > .999f &&
        Hit.ImpactPoint.Z - FrameFloorZ > MaxStepHeight + .1f);
}

void UMonsterCharacterMovementComponent::ConfigureWideBodyStairs(float NavigationRadius, float NavigationHeight)
{
    MaxStepHeight = 40.f;
    // A full-radius flat box can intersect several higher risers before the
    // broad capsule reaches them, leaving only a line floor below its centre.
    // Use UE's capsule support; IsWalkable still rejects an over-height tread,
    // and StepUp retains swept clearance, edge tolerance and failed-move rollback.
    bUseFlatBaseForFloorChecks = false;
    SetUpdateNavAgentWithOwnersCollisions(false);
    auto& Agent = GetNavAgentPropertiesRef();
    Agent.AgentRadius = NavigationRadius;
    Agent.AgentHeight = NavigationHeight;
    Agent.AgentStepHeight = MaxStepHeight;
}

void UMonsterCharacterMovementComponent::RefreshFloorReference()
{
    bHaveFrameFloor = IsMovingOnGround() && CurrentFloor.IsWalkableFloor() && UpdatedComponent && CharacterOwner;
    if (bHaveFrameFloor)
    {
        // SetFromLineTrace retains the rejected sweep's ImpactPoint.
        FrameFloorZ = CurrentFloor.bLineTrace ? UpdatedComponent->GetComponentLocation().Z -
            CharacterOwner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() - CurrentFloor.LineDist :
            CurrentFloor.HitResult.ImpactPoint.Z;
    }
}

void UMonsterCharacterMovementComponent::MoveAlongFloor(const FVector& InVelocity, float DeltaSeconds,
    FStepDownResult* OutStepDownResult)
{
    // PhysWalking may accept more than one step within a frame. The next
    // substep must compare against that accepted support, not the tick's first floor.
    RefreshFloorReference();
    Super::MoveAlongFloor(InVelocity, DeltaSeconds, OutStepDownResult);
}

bool UMonsterCharacterMovementComponent::CanOffsetMesh() const
{
    const auto* Mesh = CharacterOwner ? CharacterOwner->GetMesh() : nullptr;
    // A detached/simulated corpse owns its world transform. Network proxies retain
    // the engine's network mesh smoothing; this presentation is for local simulation.
    return Mesh && Mesh->GetAttachParent() == UpdatedComponent &&
        !Mesh->IsSimulatingPhysics() && CharacterOwner->GetLocalRole() != ROLE_SimulatedProxy;
}

void UMonsterCharacterMovementComponent::ApplyMeshOffset(float Offset)
{
    auto* Mesh = CharacterOwner->GetMesh();
    const FVector Base = Mesh->GetRelativeLocation() - AppliedRelativeOffset;
    AppliedRelativeOffset = UpdatedComponent->GetComponentTransform().InverseTransformVector(FVector(0, 0, Offset));
    Mesh->SetRelativeLocation(Base + AppliedRelativeOffset);
    MeshStairOffset = Offset;
}

void UMonsterCharacterMovementComponent::TickComponent(float DeltaTime, ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    RefreshFloorReference();
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    // Freeze at the last visible pose on death; never pull a corpse back to its capsule.
    if (!CanOffsetMesh() || MovementMode == MOVE_None) return;

    float Offset = MeshStairOffset;
    if (IsMovingOnGround()) Offset -= GetFrameStairDisplacement();
    const float Speed = FMath::Max(StairVisualSpeed, float(Velocity.Size2D()) * StairSpeedToWalkSpeed);
    ApplyMeshOffset(FMath::FInterpConstantTo(Offset, 0.f, DeltaTime, Speed));
}

void UMonsterCharacterMovementComponent::OnTeleported()
{
    bHaveFrameFloor = false;
    Super::OnTeleported();
    if (CanOffsetMesh()) ApplyMeshOffset(0.f);
}
