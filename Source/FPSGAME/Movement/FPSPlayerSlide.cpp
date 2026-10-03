#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"

void AFPSGAMECharacter::ApplyNetSlideFlag(bool bSliding, bool bFullEntry)
{
    if (bSliding == bIsSliding) return;
    if (bSliding)
    {
        if (bFullEntry) { StartSlide(); return; }
        bIsSliding = true;
        bSlideDownhill = false;
        SlideAge = 0.0f;
        SlideTimeRemaining = SlideMaximumTime;
        UCharacterMovementComponent* Movement = GetCharacterMovement();
        Movement->GroundFriction = 0.0f;
        Movement->BrakingDecelerationWalking = 0.0f;
    }
    else
    {
        StopSlide(false);
    }
}

void AFPSGAMECharacter::UpdateSlide(float DeltaSeconds)
{
    UCharacterMovementComponent* Movement = GetCharacterMovement();
    const float PreviousSlideAge = SlideAge;
    SlideAge += DeltaSeconds;
    FVector HorizontalVelocity(Movement->Velocity.X, Movement->Velocity.Y, 0.f);
    const float Speed = HorizontalVelocity.Size();
    // Check actual collision-constrained speed before restoring downhill speed:
    // a wall, disabled movement or a higher-priority action must still end it.
    if (Speed <= CrouchSpeed || IsTraversing() || IsDodging() || IsMeleeSkillMovementLocked()
        || (Controller && Controller->IsMoveInputIgnored())
        || (!Movement->IsMovingOnGround() && !Movement->IsFalling()))
    {
        StopSlide(false);
        return;
    }

    const UCapsuleComponent* Capsule = GetCapsuleComponent();
    const FVector Direction = HorizontalVelocity / Speed;
    const FVector Feet = GetActorLocation() - FVector(0.f, 0.f, Capsule->GetScaledCapsuleHalfHeight());
    FCollisionQueryParams Params(SCENE_QUERY_STAT(SlideDownhill), false, this);
    const FCollisionResponseParams Responses(Capsule->GetCollisionResponseToChannels());
    const auto TraceFloor = [&](const FVector& Position, float Up, float Down, FHitResult& Hit)
    {
        return GetWorld()->LineTraceSingleByChannel(Hit, Position + FVector(0.f, 0.f, Up),
            Position - FVector(0.f, 0.f, Down), Capsule->GetCollisionObjectType(), Params, Responses)
            && Movement->IsWalkable(Hit);
    };

    FHitResult FloorHit;
    if (Movement->IsMovingOnGround() && Movement->CurrentFloor.IsWalkableFloor())
    {
        FloorHit = Movement->CurrentFloor.HitResult;
    }
    else if (!(bSlideDownhill && Movement->IsFalling() && Movement->Velocity.Z <= 0.f
        && TraceFloor(Feet, 4.f, Movement->MaxStepHeight + 4.f, FloorHit)))
    {
        // Only an already-descending slide can bridge a normal-height stair
        // drop. Jumps call StopSlide before launch; open ledges end the slide.
        StopSlide(false);
        return;
    }

    // A surface is downhill only along travel, not merely because it is tilted.
    // 3.5% grade ignores tiny collision seams without excluding gentle hills.
    constexpr float MinimumDownhillGrade = .035f;
    const float Grade = FVector::DotProduct(Direction, FloorHit.ImpactNormal)
        / FMath::Max(.01f, float(FloorHit.ImpactNormal.Z));
    bool bDownhill = Grade > MinimumDownhillGrade;
    if (!bDownhill && Grade >= -MinimumDownhillGrade)
    {
        // Individual stair treads are horizontal. Read the next support height
        // within a bounded look-ahead, using the capsule's collision responses.
        const float ProbeDistance = FMath::Clamp(Speed * .075f, 45.f, 100.f);
        const float WalkableZ = FMath::Max(.1f, Movement->GetWalkableFloorZ());
        const float MaximumGrade = FMath::Sqrt(FMath::Max(0.f, 1.f - WalkableZ * WalkableZ)) / WalkableZ;
        const float ProbeDepth = Movement->MaxStepHeight + ProbeDistance * MaximumGrade;
        const FVector ProbeOrigin(Feet.X + Direction.X * ProbeDistance,
            Feet.Y + Direction.Y * ProbeDistance, FloorHit.ImpactPoint.Z);
        FHitResult Ahead;
        if (TraceFloor(ProbeOrigin, Movement->MaxStepHeight + 4.f, ProbeDepth, Ahead))
        {
            const float Drop = FloorHit.ImpactPoint.Z - Ahead.ImpactPoint.Z;
            bDownhill = Drop > FMath::Max(2.f, ProbeDistance * MinimumDownhillGrade);
        }
    }

    bSlideDownhill = bDownhill;
    if (bDownhill)
    {
        // Gravity sustains the configured slide maximum rather than fighting
        // exponential drag and the flat-ground timeout. Never stack new boosts.
        const auto* Status = FindComponentByClass<UCombatStatusFormula>();
        const float StatusMultiplier = Status ? Status->MovementMultiplier() : 1.f;
        HorizontalVelocity = Direction * SprintSpeed * SlideSpeedMultiplier * StatusMultiplier;
        SlideTimeRemaining = SlideMaximumTime;
    }
    else
    {
        // Landing on the flat resumes the original slide decay and time budget.
        SlideTimeRemaining -= DeltaSeconds;
        HorizontalVelocity *= FMath::Exp(-SlideFriction * DeltaSeconds);
        const FVector DownSlope = FVector::VectorPlaneProject(FVector(0.f, 0.f, -2000.f), FloorHit.ImpactNormal);
        HorizontalVelocity += FVector(DownSlope.X, DownSlope.Y, 0.f) * DeltaSeconds;
    }
    Movement->Velocity.X = HorizontalVelocity.X;
    Movement->Velocity.Y = HorizontalVelocity.Y;
    // Resolve the elapsed slide time before this frame's decay can end it.
    // Otherwise a threshold crossing on the last slide frame is silently lost.
    // StartSlide resets the age; sustained downhill slides still trigger once.
    constexpr float CowboyReloadDelay = .25f;
    if (PreviousSlideAge < CowboyReloadDelay && SlideAge >= CowboyReloadDelay) TryCowboyReload();
    if (SlideTimeRemaining <= 0.f || HorizontalSpeed() <= CrouchSpeed) StopSlide(false);
}
