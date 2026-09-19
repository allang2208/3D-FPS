#include "../FPSGAMECharacter.h"
#include "../Movement/FPSFootstepAudioComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

void AFPSGAMECharacter::ResetRifleLocomotion()
{
    LocomotionLaggedVelocity = GetVelocity();
    RifleInertiaOffset = RifleInertiaVelocity = FVector::ZeroVector;
    RifleInertiaAngles = RifleInertiaAngularVelocity = FVector::ZeroVector;
    RifleLocomotionWeight = 0.f;
    bLocomotionInitialized = true;
}

void AFPSGAMECharacter::UpdateLocomotionPresentation(float DeltaSeconds)
{
    const FVector Velocity = GetVelocity();
    const float Speed = Velocity.Size2D();
    const bool bGroundStride = GetCharacterMovement()->IsMovingOnGround()
        && !bIsSliding && !IsDodging() && !IsTraversing();
    const float MoveTarget = bGroundStride
        ? FMath::Clamp((Speed - 15.f) / FMath::Max(WalkSpeed - 15.f, 1.f), 0.f, 1.f) : 0.f;
    GroundLocomotionWeight = FMath::Lerp(GroundLocomotionWeight, MoveTarget,
        1.f - FMath::Exp(-12.f * DeltaSeconds));

    // Audio already owns distance, left/right contacts, crouch and speed changes.
    // Sample its render-rate phase once for both camera and rifle presentation.
    if (bGroundStride && Speed > 15.f)
    {
        if (const auto* Footsteps = FindComponentByClass<UFPSFootstepAudioComponent>())
            CameraBobPhase = Footsteps->GetStridePhaseRadians();
    }
    M4SprintPhase = CameraBobPhase;

    const FRotator ViewYaw(0.f, GetControlRotation().Yaw, 0.f);
    const FVector LocalVelocity = ViewYaw.UnrotateVector(Velocity);
    const float SideTarget = bGroundStride
        ? FMath::Clamp(LocalVelocity.Y / FMath::Max(WalkSpeed, 1.f), -1.f, 1.f) : 0.f;
    LocomotionSideAlpha = FMath::Lerp(LocomotionSideAlpha, SideTarget,
        1.f - FMath::Exp(-10.f * DeltaSeconds));

    if (!bInventoryWeaponReady || IsPistolWeapon() || IsDualWieldingPistols())
    {
        ResetRifleLocomotion();
        return;
    }
    if (!bLocomotionInitialized) ResetRifleLocomotion();

    // World-space velocity history makes actual acceleration drive the response;
    // merely turning the camera while stationary cannot invent movement inertia.
    LocomotionLaggedVelocity = FMath::Lerp(LocomotionLaggedVelocity, Velocity,
        1.f - FMath::Exp(-8.f * DeltaSeconds));
    const FVector Lag = ViewYaw.UnrotateVector(LocomotionLaggedVelocity - Velocity);
    const bool bAction = IsWeaponBusy() || IsTraversing() || IsDodging()
        || IsCastBlockingLeftHandAction() || bGunsmithInspection;
    const float PresentationTarget = bAction ? 0.f : (bFireHeld ? .4f : 1.f);
    RifleLocomotionWeight = FMath::Lerp(RifleLocomotionWeight, PresentationTarget,
        1.f - FMath::Exp(-(bAction ? 28.f : 12.f) * DeltaSeconds));

    FVector OffsetTarget = FVector::ZeroVector;
    FVector AngleTarget = FVector::ZeroVector;
    if (bGroundStride && !bAction)
    {
        OffsetTarget = FVector(FMath::Clamp(Lag.X * .006f, -1.4f, 1.4f),
            FMath::Clamp(Lag.Y * .004f, -.9f, .9f), 0.f) * RifleLocomotionScale;
        AngleTarget = FVector(FMath::Clamp(-Lag.X * .003f, -.65f, .65f),
            FMath::Clamp(Lag.Y * .002f, -.45f, .45f), -LocomotionSideAlpha * .65f)
            * RifleLocomotionScale;
    }

    // Reuse the project's analytic damped spring, solving around this frame's
    // target. No extra physics tick, trace, asset, or gameplay recoil is involved.
    RifleInertiaOffset -= OffsetTarget;
    AdvanceSpring(RifleInertiaOffset, RifleInertiaVelocity, 220.f, 27.f, DeltaSeconds);
    RifleInertiaOffset += OffsetTarget;
    RifleInertiaAngles -= AngleTarget;
    AdvanceSpring(RifleInertiaAngles, RifleInertiaAngularVelocity, 260.f, 29.f, DeltaSeconds);
    RifleInertiaAngles += AngleTarget;
}
