#include "../FPSGAMECharacter.h"
#include "../Movement/FPSFootstepAudioComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

void AFPSGAMECharacter::ResetPistolLocomotion()
{
    PistolLocomotionAlpha = 0.f;
    PistolLocomotionOffset = FVector::ZeroVector;
    PistolLocomotionRotation = FRotator::ZeroRotator;
    PistolLaggedVelocity = GetVelocity();
    PistolSprintPhase = 0.f;
}

void AFPSGAMECharacter::UpdatePistolLocomotion(float DeltaSeconds)
{
    if (!IsPistolWeapon())
    {
        ResetPistolLocomotion();
        return;
    }
    const bool bGroundStride = GetCharacterMovement()->IsMovingOnGround()
        && !bIsSliding && !IsDodging() && !IsTraversing();
    const float Speed = HorizontalSpeed();
    if (bGroundStride && Speed > 15.f)
        if (const auto* Footsteps = FindComponentByClass<UFPSFootstepAudioComponent>())
            PistolSprintPhase = Footsteps->GetStridePhaseRadians();

    PistolLocomotionAlpha = SprintPoseFactor * SprintPoseFactor * (3.f - 2.f * SprintPoseFactor);
    const bool bAction = IsWeaponBusy() || bIsAiming || bFireHeld
        || IsTraversing() || IsDodging() || IsCastBlockingLeftHandAction();
    const float PresentationWeight = bAction ? 0.f : 1.f;
    const float WalkWeight = bGroundStride ? FMath::Clamp(Speed / FMath::Max(WalkSpeed, 1.f), 0.f, 1.f)
        * (1.f - PistolLocomotionAlpha) : 0.f;
    const float Side = FMath::Cos(PistolSprintPhase);
    const float Step = FMath::Cos(2.f * PistolSprintPhase);

    // Walk and sprint share footstep phase. The baked sprint owns the large arc;
    // this layer only adds a quiet two-hand walk, breathing and acceleration lag.
    FVector Offset(PistolWalkAmplitudeCM.X * FMath::Sin(2.f * PistolSprintPhase),
        PistolWalkAmplitudeCM.Y * Side, -PistolWalkAmplitudeCM.Z * Step);
    Offset *= WalkWeight;
    const float BreathWeight = (1.f - FMath::Clamp(Speed / 100.f, 0.f, 1.f)) * (1.f - PistolLocomotionAlpha);
    Offset += FVector(0.f, .45f * FMath::Sin(FeedbackTime * 1.9f), FMath::Sin(FeedbackTime * 2.1f))
        * PistolIdleBreathCM * BreathWeight;

    const FVector Velocity = GetVelocity();
    PistolLaggedVelocity = FMath::Lerp(PistolLaggedVelocity, Velocity, 1.f - FMath::Exp(-8.f * DeltaSeconds));
    const FVector Lag = FRotator(0.f, GetControlRotation().Yaw, 0.f)
        .UnrotateVector(PistolLaggedVelocity - Velocity);
    if (bGroundStride)
        Offset += FVector(FMath::Clamp(Lag.X * .005f, -1.2f, 1.2f),
            FMath::Clamp(Lag.Y * .004f, -.8f, .8f), 0.f);
    const float Follow = 1.f - FMath::Exp(-(bAction ? 28.f : 18.f) * DeltaSeconds);
    PistolLocomotionOffset = FMath::Lerp(PistolLocomotionOffset, Offset * PresentationWeight, Follow);
    const FRotator Turn(.20f * FMath::Sin(2.f * PistolSprintPhase) * WalkWeight,
        .40f * FMath::Cos(PistolSprintPhase - .25f) * WalkWeight,
        -.55f * Side * WalkWeight);
    PistolLocomotionRotation = FMath::Lerp(PistolLocomotionRotation, Turn * PresentationWeight, Follow);
}
