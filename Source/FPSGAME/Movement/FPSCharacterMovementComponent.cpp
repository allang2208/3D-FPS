#include "FPSCharacterMovementComponent.h"
#include "Components/SceneComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/Controller.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

bool UFPSCharacterMovementComponent::DoJump(bool bReplayingMoves, float DeltaTime)
{
    if (IsDodging()) return false;
    const bool Result=Super::DoJump(bReplayingMoves,DeltaTime);
    if(Result) bLeavingStairJump=bLastFrameSteppedUp;
    if(FParse::Param(FCommandLine::Get(),TEXT("StairMovementAudit")))
        UE_LOG(LogTemp,Display,TEXT("STAIR_JUMP accepted=%d z=%.3f vz=%.3f offset=%.3f"),Result,UpdatedComponent->GetComponentLocation().Z,Velocity.Z,StairVisualOffset);
    return Result;
}

bool UFPSCharacterMovementComponent::IsValidLandingSpot(const FVector& CapsuleLocation,const FHitResult& Hit) const
{
    // At high tick rates the rounded foot can touch the same step immediately
    // after jumping. That contact must not consume an upward jump as a landing.
    // Collision deflection still runs; ordinary descending landings are unchanged.
    if(bLeavingStairJump && FVector::DotProduct(Velocity,-GetGravityDirection())>0.f) return false;
    return Super::IsValidLandingSpot(CapsuleLocation,Hit);
}

UFPSCharacterMovementComponent::UFPSCharacterMovementComponent()
{
    MaxStepHeight = 40.f;
}

bool UFPSCharacterMovementComponent::StepUp(const FVector& GravDir, const FVector& Delta,
    const FHitResult& Hit, FStepDownResult* OutStepDownResult)
{
    const FVector Before = UpdatedComponent->GetComponentLocation();
    // Keep the engine's capsule sweeps, headroom, walkable floor, perching and rollback rules.
    const bool bStepped = Super::StepUp(GravDir, Delta, Hit, OutStepDownResult);
    if (bCaptureStairs && bStepped)
        FrameStairDisplacement += float(UpdatedComponent->GetComponentLocation().Z - Before.Z);
    return bStepped;
}

void UFPSCharacterMovementComponent::AdjustFloorHeight()
{
    const double BeforeZ = UpdatedComponent->GetComponentLocation().Z;
    Super::AdjustFloorHeight();
    if (bCaptureStairs)
        FrameStairDisplacement += float(UpdatedComponent->GetComponentLocation().Z - BeforeZ);
}

void UFPSCharacterMovementComponent::TickComponent(float DeltaTime, ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    if (DodgeRootMotionId && (MovementMode==MOVE_None ||
        (CharacterOwner && CharacterOwner->Controller && CharacterOwner->Controller->IsMoveInputIgnored())))
        CancelDodge();
    FrameStairDisplacement = 0.f;
    bCaptureStairs = IsMovingOnGround();
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    UpdateDodgeState();
    bCaptureStairs = false;
    bLastFrameSteppedUp = IsMovingOnGround() && FrameStairDisplacement > .1f;
    if (IsMovingOnGround()) bLeavingStairJump = false;
    if (!StairVisualRoot || !CharacterOwner || !CharacterOwner->IsLocallyControlled()) return;

    // Only accepted step/floor corrections contribute: slope travel, moving bases,
    // crouch capsule resizing, jumping and landing retain their native trajectory.
    if (IsMovingOnGround()) StairVisualOffset -= FrameStairDisplacement;
    const float Speed = FMath::Max(StairVisualSpeed, float(Velocity.Size2D()) * StairSpeedToWalkSpeed);
    StairVisualOffset = FMath::FInterpConstantTo(StairVisualOffset, 0.f, DeltaTime, Speed);
    StairVisualRoot->SetRelativeLocation(FVector(0, 0, StairVisualOffset));
}

void UFPSCharacterMovementComponent::OnTeleported()
{
    CancelDodge();
    Super::OnTeleported();
    FrameStairDisplacement = StairVisualOffset = 0.f;
    bLastFrameSteppedUp = bLeavingStairJump = false;
    if (StairVisualRoot) StairVisualRoot->SetRelativeLocation(FVector::ZeroVector);
}
