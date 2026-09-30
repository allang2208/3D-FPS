#include "../FPSGAMECharacter.h"
#include "WeaponBipodDeploymentComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"

namespace WeaponCrouchPose
{
    // Project tuning inspired by the Apex hip-fire crouch gesture, not extracted
    // Apex angles. Camera axes: X forward, Y right, Z up; distances in cm.
    constexpr float RifleCantDegrees = 18.f;
    constexpr float PistolCantDegrees = 12.f;
    constexpr float EnterSeconds = .18f;
    constexpr float ExitSeconds = .22f;
    constexpr float ActionReturnSeconds = .10f;

    float Ease(float Progress)
    {
        return Progress * Progress * Progress * (Progress * (Progress * 6.f - 15.f) + 10.f);
    }
}

void AFPSGAMECharacter::UpdateWeaponCrouchPose(float DeltaSeconds)
{
    if (!bInventoryWeaponReady)
    {
        WeaponCrouchProgress = 0.f;
        return;
    }

    // Hip fire retains the stance. Reloads, equip, melee and casting own their
    // authored framing; this presentation layer never holds up their clocks.
    const bool bAction = IsSwitchingWeapon() || IsWeaponBusy()
        || IsCastBlockingLeftHandAction() || bGunsmithInspection
        || IsTraversing() || IsDodging();
    // Slide intent is available before the movement component finishes crouching.
    // Sharing the target/progress also keeps slide -> crouch from returning upright.
    const bool bLowStance = (bIsCrouched || bIsSliding) && !bWeaponJumpAirborne && GetCharacterMovement()->IsMovingOnGround()
        && !bIsSprinting && !bAction;
    // Carry the current slide cant into takeoff and unwind over the early rise.
    // No reset at launch: a half-entered slide starts from its visible progress.
    const bool bSlideJumpHandoff = GetWorld()->GetTimeSeconds() - LastSlideJumpAt < .42;
    const float Duration = bLowStance ? WeaponCrouchPose::EnterSeconds
        : bAction ? WeaponCrouchPose::ActionReturnSeconds : bSlideJumpHandoff ? .34f : WeaponCrouchPose::ExitSeconds;
    // A direction change continues from the current progress, including a quick
    // crouch tap. Finite blending reaches the exact standing pose again.
    WeaponCrouchProgress = FMath::FInterpConstantTo(WeaponCrouchProgress,
        bLowStance ? 1.f : 0.f, DeltaSeconds, 1.f / Duration);
}

void AFPSGAMECharacter::ApplyWeaponCrouchPose(FVector& Location, FQuat& Rotation,
    bool bPistol, bool bLeftHand) const
{
    const float HipWeight = 1.f - WeaponADSFactor;
    const float FreeWeaponWeight = BipodDeployment ? 1.f - BipodDeployment->GetDeploymentBlend() : 1.f;
    const float Weight = WeaponCrouchPose::Ease(WeaponCrouchProgress)
        * HipWeight * HipWeight * FreeWeaponWeight;
    if (Weight <= SMALL_NUMBER) return;

    // Rotate around a camera-space grip region, not the imported mesh origin.
    // The mirrored off-hand pistol inclines inward toward the same screen centre.
    const float Side = bLeftHand ? -1.f : 1.f;
    const FVector Pivot = bPistol ? FVector(20.f, 6.f * Side, -8.f)
        : FVector(25.f, 10.f, -12.f);
    const FVector Tuck = bPistol ? FVector(-.6f, -.65f * Side, -.4f)
        : FVector(-1.f, -1.25f, -.8f);
    const float Angle = bPistol ? WeaponCrouchPose::PistolCantDegrees : WeaponCrouchPose::RifleCantDegrees;
    // Positive axis-angle about camera X sends the top of the right-hand gun
    // toward camera-left (equivalent to a negative UE Rotator Roll).
    const FQuat Cant(FVector::ForwardVector, FMath::DegreesToRadians(Angle * Side * Weight));
    Location = Pivot + Cant.RotateVector(Location - Pivot) + Tuck * Weight;
    Rotation = (Cant * Rotation).GetNormalized();
}
