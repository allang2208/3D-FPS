#include "../FPSGAMECharacter.h"
#include "RuneSwordComponent.h"
#include "WeaponBipodDeploymentComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"

namespace WeaponJumpPose
{
    float Ease(float T) { return T*T*T*(T*(T*6.f-15.f)+10.f); }
}

void AFPSGAMECharacter::UpdateWeaponJumpPose(float DeltaSeconds)
{
    if (DeltaSeconds <= 0.f) return;
    const auto* Movement = GetCharacterMovement();
    const FVector Velocity = GetVelocity();
    const bool bFalling = Movement->IsFalling();
    const double SlideJumpAge = GetWorld()->GetTimeSeconds() - LastSlideJumpAt;
    // LaunchCharacter consumes its pending launch on the movement tick. Do not
    // re-enter a sprint carry in the frame between uncrouching and taking off.
    bWeaponJumpAirborne = bFalling || SlideJumpAge < .10;
    const bool bAction = IsSwitchingWeapon() || IsWeaponBusy() || IsCastBlockingLeftHandAction()
        || bGunsmithInspection || IsTraversing() || IsDodging();
    const bool bHasRig = bInventoryWeaponReady || (RuneSword && RuneSword->IsEquipped());
    WeaponJumpActionProgress = FMath::FInterpConstantTo(WeaponJumpActionProgress,
        bHasRig && !bAction ? 1.f : 0.f, DeltaSeconds, bAction ? 12.5f : 6.25f);

    if (!bWeaponJumpInitialized)
    {
        bWeaponWasFalling = bFalling;
        WeaponJumpPreviousVerticalSpeed = Velocity.Z;
        bWeaponJumpInitialized = true;
    }
    if (bFalling && !bWeaponWasFalling)
    {
        WeaponAirSeconds = 0.f;
        WeaponJumpSide = FMath::Cos(M4SprintPhase);
        WeaponJumpMomentum = 1.f + .15f * FMath::Clamp(Velocity.Size2D() / FMath::Max(SprintSpeed, 1.f), 0.f, 1.f);
        // An actual upward launch gets a short inertial dip. Walking off a ledge
        // only gets the falling response, never a fabricated jump impulse.
        if (Velocity.Z > 120.f && !IsTraversing() && !IsDodging())
        {
            const float Strength = FMath::Clamp(float(Velocity.Z) / 650.f, 0.f, 1.2f)
                * (SlideJumpAge < .25 ? 1.15f : 1.f);
            WeaponJumpVelocity += FVector(-4.f, .9f * WeaponJumpSide, -14.f) * Strength;
            WeaponJumpAngularVelocity += FVector(-16.f, 2.f * WeaponJumpSide, 6.f * WeaponJumpSide) * Strength;
        }
    }
    else if (bWeaponWasFalling && Movement->IsMovingOnGround())
    {
        const float Impact = FMath::Clamp(-WeaponJumpPreviousVerticalSpeed / 650.f, 0.f, 1.5f);
        WeaponJumpVelocity += FVector(-2.f, 1.2f * WeaponJumpSide, -22.f) * Impact;
        WeaponJumpAngularVelocity += FVector(-22.f, 0.f, -7.f * WeaponJumpSide) * Impact;
    }
    bWeaponWasFalling = bFalling;
    WeaponJumpPreviousVerticalSpeed = Velocity.Z;
    if (bFalling) WeaponAirSeconds += DeltaSeconds;

    FVector OffsetTarget = FVector::ZeroVector, AngleTarget = FVector::ZeroVector;
    if (bFalling && !IsTraversing() && !IsDodging())
    {
        const float Rise = FMath::Clamp(float(Velocity.Z) / 650.f, 0.f, 1.f);
        const float Fall = FMath::Clamp(float(-Velocity.Z) / 650.f, 0.f, 1.f);
        // A short decaying lateral settle, not a looping walk or random shake.
        // Vertical velocity carries the dip through ascent, apex and descent.
        const float Settle = FMath::Sin(WeaponAirSeconds * 9.f) * FMath::Exp(-4.f * WeaponAirSeconds) * WeaponJumpSide;
        OffsetTarget = FVector(-.5f * Rise, .18f * Settle, -.75f * Rise + .45f * Fall) * WeaponJumpMomentum;
        AngleTarget = FVector(-1.15f * Rise + .7f * Fall, .15f * Settle, .45f * Settle);
    }
    // Keep position and velocity through takeoff, landing and repeated jumps.
    // The existing analytic spring avoids frame-count-dependent recoil pulses.
    WeaponJumpOffset -= OffsetTarget;
    AdvanceSpring(WeaponJumpOffset, WeaponJumpVelocity, 180.f, 20.f, DeltaSeconds);
    WeaponJumpOffset += OffsetTarget;
    WeaponJumpAngles -= AngleTarget;
    AdvanceSpring(WeaponJumpAngles, WeaponJumpAngularVelocity, 150.f, 18.f, DeltaSeconds);
    WeaponJumpAngles += AngleTarget;
}

FTransform AFPSGAMECharacter::GetWeaponJumpTransform(EFirstPersonJumpRig Rig, bool bLeftHand) const
{
    const bool bSword = Rig == EFirstPersonJumpRig::Sword;
    const bool bPistol = Rig == EFirstPersonJumpRig::Pistol;
    const float HipWeight = bSword ? 1.f : FMath::Square(1.f - WeaponADSFactor);
    const float FreeWeight = bSword || !BipodDeployment ? 1.f : 1.f - BipodDeployment->GetDeploymentBlend();
    const float Weight = WeaponJumpPose::Ease(WeaponJumpActionProgress) * HipWeight * FreeWeight;
    const float Side = bLeftHand ? -1.f : 1.f;
    FVector Offset = WeaponJumpOffset * Weight * (bSword ? 1.05f : bPistol ? .75f : 1.f);
    FVector Angles = WeaponJumpAngles * Weight * (bSword ? .65f : bPistol ? .85f : 1.f);
    Offset.Y *= Side; Angles.Y *= Side; Angles.Z *= Side;
    const FVector Pivot = bSword ? FVector(25.f, 0.f, -12.f)
        : FVector(20.f, 8.f * Side, -10.f);
    const FQuat Turn = FRotator(Angles.X, Angles.Y, Angles.Z).Quaternion();
    // One rigid transform keeps both grips and every attached part together.
    return FTransform(Turn, Pivot - Turn.RotateVector(Pivot) + Offset);
}
