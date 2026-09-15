#include "FPSCharacterMovementComponent.h"
#include "Engine/ScopedMovementUpdate.h"
#include "GameFramework/Character.h"
#include "GameFramework/Controller.h"

FVector UFPSCharacterMovementComponent::ApplyMeleeLungeStep(const FVector& Direction,float DistanceCM)
{
    if(!CharacterOwner || !UpdatedComponent || GetNetMode()!=NM_Standalone ||
        !IsMovingOnGround() || IsDodging() || !CurrentFloor.IsWalkableFloor() || DistanceCM<=0.f)
        return FVector::ZeroVector;
    const auto* Controller=CharacterOwner->GetController();
    if(!Controller || Controller->IsMoveInputIgnored())return FVector::ZeroVector;

    const FVector Start=UpdatedComponent->GetComponentLocation();
    const FVector Forward=Direction.GetSafeNormal2D();
    float Remaining=DistanceCM;
    // A metre-long stride can span a ledge during one slow frame. Check ground
    // support in short swept steps, retaining accepted movement up to the edge.
    while(Remaining>UE_SMALL_NUMBER)
    {
        const float StepDistance=FMath::Min(Remaining,5.f);
        const FVector StepStart=UpdatedComponent->GetComponentLocation();
        const FVector Delta=ComputeGroundMovementDelta(Forward*StepDistance,
            CurrentFloor.HitResult,CurrentFloor.bLineTrace);
        FFindFloorResult Floor;
        FindFloor(StepStart+Delta,Floor,false);
        if(!Floor.IsWalkableFloor() || Floor.GetDistanceToFloor()>MaxStepHeight+MAX_FLOOR_DIST)break;

        FScopedMovementUpdate Movement(UpdatedComponent,EScopedUpdate::DeferredUpdates);
        FHitResult Hit;
        SafeMoveUpdatedComponent(Delta,UpdatedComponent->GetComponentQuat(),true,Hit);
        FindFloor(UpdatedComponent->GetComponentLocation(),Floor,false);
        if(!Floor.IsWalkableFloor() || Floor.GetDistanceToFloor()>MaxStepHeight+MAX_FLOOR_DIST)
        {
            Movement.RevertMove();
            break;
        }
        CurrentFloor=Floor;bForceNextFloorCheck=true;
        Remaining-=StepDistance;
        const float Travel=FVector::DotProduct(UpdatedComponent->GetComponentLocation()-StepStart,Forward);
        if(Hit.bBlockingHit || Travel+.01f<StepDistance)break;
    }
    return UpdatedComponent->GetComponentLocation()-Start;
}
