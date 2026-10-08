#include "FPSCharacterMovementComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "Engine/ScopedMovementUpdate.h"
#include "GameFramework/Character.h"
#include "GameFramework/Controller.h"

bool UFPSCharacterMovementComponent::BeginMeleeDashMomentum(const FVector& IncomingVelocity)
{
    if(UBoundCongregateCaptureComponent::IsCaptured(CharacterOwner))return false;
    if(!CharacterOwner || !UpdatedComponent || GetNetMode()==NM_Client ||
        (!IsMovingOnGround() && !IsFalling()) || IncomingVelocity.ContainsNaN() ||
        IncomingVelocity.SizeSquared2D()<=1.f)return false;
    Velocity.X=IncomingVelocity.X;
    Velocity.Y=IncomingVelocity.Y;
    bMeleeDashMomentum=true;
    UpdateComponentVelocity();
    return true;
}

void UFPSCharacterMovementComponent::CalcVelocity(float DeltaTime,float Friction,bool bFluid,float BrakingDeceleration)
{
    if(IsBipodMovementLocked()&&IsMovingOnGround())
    {bMeleeDashMomentum=false;Velocity=FVector::ZeroVector;Acceleration=FVector::ZeroVector;return;}
    if(bMeleeDashMomentum)
    {
        const auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);
        const auto* Status=CharacterOwner?CharacterOwner->FindComponentByClass<UCombatStatusFormula>():nullptr;
        const bool bInputResumed=Player && !Player->IsMeleeSkillMovementLocked() && !Acceleration.IsNearlyZero();
        if(!Player || IsDodging() || (!IsMovingOnGround() && !IsFalling()) ||
            (Player->Controller && Player->Controller->IsMoveInputIgnored()) ||
            (Status && Status->BlocksMovement()) || bInputResumed)
        {
            bMeleeDashMomentum=false;
        }
        else
        {
            if(!HasValidData() || HasAnimRootMotion() || DeltaTime<MIN_TICK_TIME)return;
            // Brake the real, collision-constrained velocity. Never restore a
            // cached speed after hitting a wall, or add the fixed one-metre step.
            // Native walking/falling still owns capsule sweeps and gravity.
            constexpr float AirDeceleration=300.f;
            constexpr float GroundDeceleration=1800.f;
            const double VerticalSpeed=Velocity.Z;
            Velocity.Z=0.;
            ApplyVelocityBraking(DeltaTime,0.f,IsFalling()?AirDeceleration:GroundDeceleration);
            Velocity.Z=VerticalSpeed;
            if(Velocity.SizeSquared2D()<=1.f)bMeleeDashMomentum=false;
            return;
        }
    }
    Super::CalcVelocity(DeltaTime,Friction,bFluid,BrakingDeceleration);
}

void UFPSCharacterMovementComponent::StopMovementImmediately()
{
    bMeleeDashMomentum=false;
    Super::StopMovementImmediately();
}

FVector UFPSCharacterMovementComponent::ApplyMeleeLungeStep(const FVector& Direction,float DistanceCM)
{
    if(!CharacterOwner || !UpdatedComponent || GetNetMode()==NM_Client ||
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
