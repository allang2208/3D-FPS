#include "BowWeaponComponent.h"
#include "BowMountainEchoComponent.h"
#include "BowCadenceComponent.h"
#include "../../Skills/FPSMagicArrowRainComponent.h"
#include "../../Skills/FPSElementalArrowComponent.h"
#include "../../Skills/FPSIlluminationArrowComponent.h"
#include "../../Characters/FPSComponentVisibility.h"
#include "../../Skills/LightningHasteSpeed.h"
#include "../../Combat/RangedAttackQuery.h"
#include "BowArrow.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "BowArmsMeshComponent.h"
#include "BowPartComponent.h"
#include "BowScopeOptics.h"
#include "BowQuickCombatMotion.h"
#include "BowStats.h"
#include "../../Skills/FPSQuickCombatComponent.h"
#include "../../Skills/FPSFireballComponent.h"
#include "../../Movement/FPSDoorPushComponent.h"
#include "../../Items/FPSPotionUseComponent.h"
#include "../WeaponStatEvaluation.h"
#include "../GunsmithSystem.h"
#include "../../FPSGAMECharacter.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "../../UI/ColdSteelPickup.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Building/VoxelBuildComponent.h"
#include "../../Skills/ColdSteelSkillRules.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Sound/SoundBase.h"

#include "BowWeaponPrivate.h"
using namespace BowWeaponPrivate;
bool UBowWeaponComponent::UsesCompoundOptic() const
{
    return bHasAimSight && OpticalMinimum > 1.f && EquippedDefinition == TEXT("bow_frontier_compound");
}

float UBowWeaponComponent::AimZoomAlpha() const
{
    // Finish the scoped wrist adjustment before increasing magnification.
    return UsesCompoundOptic() ? FMath::SmoothStep(.62f, 1.f, AimAlpha()) : AimAlpha();
}

float UBowWeaponComponent::PickupSeatAlpha() const
{
    if (Stage == EBowStage::Nocking)
        return FMath::SmoothStep(NockContactFraction, 1.f, Elapsed / NockSeconds);
    if (Stage == EBowStage::DrawEntry && bEntryNeedsArrow)
        return FMath::SmoothStep(.90f, 1.f, Elapsed / DrawEntrySeconds);
    return 1.f;
}

void UBowWeaponComponent::AdvanceAimWeight(float Delta, bool bTarget)
{
    // A new aim request can be held through the pickup. Start the lift when the fingers seat.
    if (bTarget && !bAimBlendTarget && UsesCompoundOptic())
    {
        const bool TakingArrow = (Stage == EBowStage::Nocking && Elapsed < NockSeconds * NockContactFraction)
            || (Stage == EBowStage::DrawEntry && bEntryNeedsArrow && Elapsed < DrawEntrySeconds * .90f);
        bTarget = !TakingArrow;
    }
    Delta*=LightningHaste::ActionSpeed(GetOwner());
    const auto BeginTravel = [this]()
    {
        AimSegmentStart = AimProgress;
        AimSegmentVelocity = AimVelocity = 0.f;
        AimSegmentElapsed = 0.f;
        bAimBraking = false;
        const float Distance = FMath::Abs((bAimBlendTarget ? 1.f : 0.f) - AimProgress);
        // A full transition keeps the catalog time. A partial return covers
        // less distance without replaying an entire raise/lower movement.
        AimSegmentDuration = (bAimBlendTarget ? AimInSeconds : AimOutSeconds) * FMath::Sqrt(Distance);
    };
    if (bTarget != bAimBlendTarget)
    {
        bAimBlendTarget = bTarget;
        AimSegmentStart = AimProgress;
        AimSegmentVelocity = AimVelocity;
        AimSegmentElapsed = 0.f;
        // Keep the old direction's velocity briefly instead of instantly
        // negating it when RMB changes midway. Stop before either endpoint.
        const float Room = AimVelocity > 0.f ? 1.f - AimProgress : AimProgress;
        AimSegmentDuration = FMath::Abs(AimVelocity) > UE_SMALL_NUMBER
            ? FMath::Min(FMath::Min(.04f, FMath::Min(AimInSeconds, AimOutSeconds) * .15f),
                1.8f * FMath::Max(0.f, Room) / FMath::Abs(AimVelocity)) : 0.f;
        bAimBraking = AimSegmentDuration > UE_SMALL_NUMBER;
        if (!bAimBraking) BeginTravel();
    }

    // One frame can finish braking and continue travelling; consume the
    // leftover delta so the path does not depend on the rendering frame rate.
    float Remaining = Delta;
    for (int32 Segment = 0; Segment < 2 && Remaining > 0.f && AimSegmentDuration > 0.f; ++Segment)
    {
        const float Step = FMath::Min(Remaining, FMath::Max(0.f, AimSegmentDuration - AimSegmentElapsed));
        AimSegmentElapsed += Step;
        Remaining -= Step;
        const float T = FMath::Clamp(AimSegmentElapsed / AimSegmentDuration, 0.f, 1.f);
        if (bAimBraking)
        {
            AimProgress = AimSegmentStart + AimSegmentVelocity * AimSegmentDuration * (T - .5f * T * T);
            AimVelocity = AimSegmentVelocity * (1.f - T);
        }
        else
        {
            // Quintic ease has zero velocity and acceleration at both ends.
            const float Ease = T * T * T * (10.f + T * (-15.f + 6.f * T));
            const float Distance = (bAimBlendTarget ? 1.f : 0.f) - AimSegmentStart;
            AimProgress = AimSegmentStart + Distance * Ease;
            AimVelocity = Distance * 30.f * T * T * FMath::Square(1.f - T) / AimSegmentDuration;
        }
        AimProgress = FMath::Clamp(AimProgress, 0.f, 1.f);
        if (AimSegmentElapsed < AimSegmentDuration) break;
        AimVelocity = 0.f;
        if (bAimBraking) BeginTravel();
        else
        {
            AimProgress = bAimBlendTarget ? 1.f : 0.f;
            AimSegmentDuration = 0.f;
        }
    }
}

void UBowWeaponComponent::AdvanceLocomotion(float Delta, bool bUsable)
{
    const auto* Pawn = Character.Get();
    const auto* Movement = Pawn ? Pawn->GetCharacterMovement() : nullptr;
    const bool bGrounded = bUsable && Movement && Movement->IsMovingOnGround();
    const float Speed = bGrounded ? float(Pawn->GetVelocity().Size2D()) : 0.f;
    const bool bCarry = bGrounded && Stage == EBowStage::Ready;
    const float MovementWeight = bCarry ? FMath::SmoothStep(8.f, 180.f, Speed) : 0.f;
    const float RunTarget = bCarry && Pawn->IsSprinting() && Speed > 80.f ? 1.f : 0.f;
    DampCarry(GaitWeight, GaitWeightVelocity, MovementWeight, 19.f, Delta);
    DampCarry(SprintBlend, SprintBlendVelocity, RunTarget, 16.f, Delta);
    DampCarry(TravelSpeed, TravelSpeedVelocity, Speed, 18.f, Delta);
    GaitWeight = FMath::Clamp(GaitWeight, 0.f, 1.f);
    SprintBlend = FMath::Clamp(SprintBlend, 0.f, 1.f);
    // Preserve phase through starts/stops and walk/run blends. No stepping in
    // mid-air; residual pose weight can still settle over the landing.
    if (bGrounded && Speed > 3.f)
        GaitPhase = FMath::Fmod(GaitPhase + Delta * FMath::Clamp(TravelSpeed, 0.f, 1000.f)
            / FMath::Lerp(430.f, 490.f, SprintBlend), 1.f);
    if (!Pawn) return;
    const float Yaw = Pawn->GetControlRotation().Yaw;
    const float TurnTarget = bUsable && bHaveViewYaw
        ? FMath::Clamp(FMath::FindDeltaAngleDegrees(PreviousViewYaw, Yaw) / Delta / 180.f, -1.f, 1.f) : 0.f;
    PreviousViewYaw = Yaw;
    bHaveViewYaw = bUsable;
    DampCarry(TurnFollow, TurnFollowVelocity, TurnTarget, 14.f, Delta);
    FVector Direction = bGrounded ? FRotator(0.f, Yaw, 0.f).UnrotateVector(Pawn->GetVelocity()) / 700.f : FVector::ZeroVector;
    Direction.Z = 0.f;
    Direction = Direction.GetClampedToMaxSize(1.f);
    DampCarry(TravelDirection, TravelDirectionVelocity, Direction, 12.f, Delta);
    const FVector Lag = (Direction - TravelDirection).GetClampedToMaxSize(.8f);
    const float Restraint = (Stage == EBowStage::Ready ? 1.f : IsDrawing() ? .15f : 0.f)
        * FMath::Lerp(1.f, .48f, CrouchProgress);
    CarryOffset = FVector(-1.4f * Lag.X, -.65f * TravelDirection.Y - .6f * Lag.Y,
        -.3f * FMath::Abs(Lag.X)) * Restraint;
    CarryRotation = FRotator(.8f * Lag.X, -.7f * TurnFollow,
        -1.3f * TravelDirection.Y - .6f * TurnFollow) * Restraint;
}

float UBowWeaponComponent::ShotSpread() const
{
    const float Low = FMath::SmoothStep(0.f, 1.f, CrouchProgress);
    const auto* Cadence=GetOwner()->FindComponentByClass<UBowCadenceComponent>();
    const float CadenceScale=Cadence&&Cadence->IsEquippedFor(InstanceId)?Cadence->SpreadMultiplier():1.f;
    return (HipSpread + MoveSpread + AirSpread + ShotBloom)
        * FMath::Lerp(1.f, CrouchSpreadScale, Low) * (1.f - AimAlpha()) * CadenceScale;
}

bool UBowWeaponComponent::ShouldShowCrosshair() const
{
    return IsEquipped() && CanUse() && Stage != EBowStage::Stowed && Stage != EBowStage::Equip
        && Character.IsValid() && !Character->IsSprinting();
}

float UBowWeaponComponent::ReleasePulse() const
{
    if (ReleaseFeedbackAge < 0.f || ReleaseFeedbackAge >= RingSeconds) return 0.f;
    const float T = ReleaseFeedbackAge;
    return ReleaseRatio * FeedbackScale * AimShakeScale() * (1.f - FMath::Exp(-160.f * T)) * FMath::Exp(-28.f * T);
}

float UBowWeaponComponent::DrawMotionWeight() const
{
    if (Stage == EBowStage::LetDown)
        return EndDrawMotionWeight * (1.f - FMath::SmoothStep(0.f, StageSeconds, Elapsed));
    const float Load = FMath::SmoothStep(0.f, 1.f, DrawFraction());
    const float Hold = Stage == EBowStage::Holding ? FMath::SmoothStep(0.f, 2.2f, HoldElapsed) : 0.f;
    return 2.f * Load * (1.f + .50f * Hold) * SwayAmplitudeCM
        * FMath::Lerp(1.f, SteadySwayScale, AimAlpha()) * FMath::Max(0.f, CVarBowSway.GetValueOnGameThread());
}

void UBowWeaponComponent::GetCameraMotion(FVector& Location, FRotator& Rotation) const
{
    Location = FVector::ZeroVector;
    Rotation = FRotator::ZeroRotator;
    if (!IsEquipped() || Elapsed < 0.f) return;
    const float Scale = (1.f - AimAlpha()) * FMath::Max(0.f, CVarBowSway.GetValueOnGameThread());
    float Ratio = DrawFraction();
    if (ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < .14f)
        Ratio = FMath::Max(Ratio, ReleaseRatio * (1.f - FMath::SmoothStep(0.f, 1.f, ReleaseFeedbackAge / .14f)));
    if (Stage == EBowStage::LetDown) Ratio = LetDownRatio * (1.f - FMath::SmoothStep(0.f, 1.f, Elapsed / StageSeconds));
    const float Kick = ReleasePulse() * FMath::Lerp(1.f, .4f, AimAlpha());
    Location += FVector(-3.2f * Ratio + .6f * Kick, 0.f, 0.f) * Scale;
    Rotation.Pitch += (-.5f * Ratio + .3f * Kick) * Scale;
    Rotation.Roll += .8f * Ratio * Scale;
    if (Stage == EBowStage::Holding)
    {
        // 满拉保持的呼吸抖动随保持时长上升；右键稳持把幅度压到配置比例。
        // Cosmetic breathing ramp only; stamina owns the duration of a held bow.
        const float Grow = FMath::Clamp(HoldElapsed / 2.2f, 0.f, 1.f);
        const float Amplitude = SwayAmplitudeCM * (.35f + .65f * Grow)
            * FMath::Lerp(1.f, SteadySwayScale, AimAlpha()) * AimShakeScale() * Scale;
        Rotation.Yaw += (FMath::Sin(VisualTime * 1.05f) + .18f * FMath::Sin(VisualTime * 4.13f)) * Amplitude * .1f;
        Rotation.Pitch += (FMath::Sin(VisualTime * .73f + 1.1f) + .15f * FMath::Sin(VisualTime * 3.37f + .4f)) * Amplitude * .085f;
    }
}

FTransform UBowWeaponComponent::AnimatedRiserMount() const
{
    return RiserMountFromGrip(Viewmodel->GetSocketTransform(TEXT("bow_grip"), RTS_Component)
        * Viewmodel->GetRelativeTransform());
}

FTransform UBowWeaponComponent::RiserMountFromGrip(FTransform Mount) const
{
    FVector Offset = FVector::ZeroVector, RotationText = FVector::ZeroVector;
    ReadVector3Text(CVarBowLocation.GetValueOnGameThread(), Offset);
    ReadVector3Text(CVarBowRotation.GetValueOnGameThread(), RotationText);
    Mount.SetScale3D(FVector(BowScale));
    Mount.AddToTranslation(GripTrimCM + Offset);
    Mount.SetRotation((FRotator(RotationText.X, RotationText.Y, RotationText.Z).Quaternion()
        * Mount.GetRotation()).GetNormalized());
    return Mount;
}

void UBowWeaponComponent::UpdatePoseLayers()
{
    if (!Pivot) return;
    if (!bHasGripMarker || !Viewmodel->IsVisible())
    {
        Pivot->SetRelativeTransform(FTransform::Identity);
        return;
    }
    // Read the unlayered animated grip, never last frame's world-space pivot.
    const FTransform Grip = Viewmodel->GetSocketTransform(TEXT("bow_grip"), RTS_Component)
        * Viewmodel->GetRelativeTransform();
    const FTransform Mount = RiserMountFromGrip(Grip);
    const FVector Nock = Stage == EBowStage::Release || Stage == EBowStage::Recover ? ReleasedNockCM : NockPoint();
    Pivot->SetRelativeTransform(PoseLayerTransform(Grip, Mount, Nock));
}

FTransform UBowWeaponComponent::PoseLayerTransform(const FTransform& Grip, const FTransform& Mount, const FVector& Nock) const
{
    const FVector GripLocation = Grip.GetLocation();
    const float Low = FMath::SmoothStep(0.f, 1.f, CrouchProgress);
    const float PushTime = Stage == EBowStage::QuickCombat
        ? Elapsed / FMath::Max(.001f, StageSeconds) * BowQuickCombatMotion::Length : 0.f;
    const float PushWeight = Stage == EBowStage::QuickCombat
        ? FMath::SmoothStep(0.f, BowQuickCombatMotion::Grip, PushTime)
            * (1.f - FMath::SmoothStep(BowQuickCombatMotion::LetGo, BowQuickCombatMotion::Length, PushTime)) : 0.f;
    // The authored push is horizontal even when entered from a crouched or
    // nocked hold. Fade the holding cant/alignment out and restore on recovery.
    FQuat HipRotation(FVector::ForwardVector,
        FMath::DegreesToRadians(CrouchCantDegrees * Low * (1.f - PushWeight)));
    HipRotation = (CarryRotation.Quaternion() * HipRotation).GetNormalized();
    const float HipAlignment = FMath::SmoothStep(0.f, 1.f, HipAimProgress) * (1.f - PushWeight);
    const FVector HipGrip = GripLocation + HipOffsetCM + CrouchOffsetCM * Low + CarryOffset;
    const FVector Rest = Mount.TransformPosition(ArrowRestCM);
    // Release keeps its aiming plane during follow-through; only the string
    // snaps back. Otherwise the changing brace axis would yaw the entire arm.
    const FVector Tail = Mount.TransformPosition(Nock);
    if (HipAlignment > 0.f)
    {
        // Aim the actual nock-to-rest line, not the bow mesh's nominal X axis.
        // Solve around the grip so the latest right/lower framing and every
        // finger/string contact stay together. The target lies on the same
        // camera-centre ray used by the crosshair, before shot randomisation.
        const FVector Axis = HipRotation.RotateVector((Rest - Tail).GetSafeNormal());
        const FVector TailFromGrip = HipRotation.RotateVector(Tail - GripLocation);
        const FVector TargetFromGrip = FVector(FMath::Max(200.f, RangeCM), 0.f, 0.f) - HipGrip;
        const double Along = FVector::DotProduct(TailFromGrip, Axis);
        const double Discriminant = FMath::Square(Along) + TargetFromGrip.SizeSquared()
            - TailFromGrip.SizeSquared();
        if (!Axis.IsNearlyZero() && Discriminant > 0.)
        {
            // A point on the arrow's extended ray at the target's radius can
            // be rotated exactly onto it while keeping the grip stationary.
            const FVector RayPoint = TailFromGrip + Axis * (-Along + FMath::Sqrt(Discriminant));
            const FQuat Correction = FQuat::FindBetweenNormals(RayPoint.GetSafeNormal(), TargetFromGrip.GetSafeNormal());
            const float Weight = FMath::SmoothStep(0.f, 1.f, HipAlignment);
            HipRotation = (FQuat::Slerp(FQuat::Identity, Correction, Weight) * HipRotation).GetNormalized();
        }
    }

    // Keep the ADS assembly forward/right/below the sight line, so the drawing
    // palm and forearm do not fill the centre of the zoomed view. Orient the
    // actual arrow axis back to the reticle instead of putting its near nock
    // directly in front of the eye. All contacts share the same rigid delta.
    const float Aim = AimAlpha();
    const float SightMotion = 1.f - Aim;
    const float Kick = ReleasePulse() * .4f * SightMotion;
    const FVector AimAnchor = bHasAimSight ? AimSightPointCM : ArrowRestCM;
    const FVector TargetAnchor = (bHasAimSight ? FVector(AimSightDistanceCM, 0.f, 0.f) : AimRestLocationCM)
        + FVector(-.45f * Kick, 0.f, -.1f * Kick);
    const bool CompoundOptic = UsesCompoundOptic();
    FVector AimTail = Nock;
    if (CompoundOptic && (Stage == EBowStage::Nocking || (Stage == EBowStage::DrawEntry && bEntryNeedsArrow)))
    {
        // The hand carries the loose arrow below the glass. Keep the mounted
        // sight on its reference axis until the fingers have seated the nock.
        AimTail = FMath::Lerp(CompoundSightNock(Nock), Nock, PickupSeatAlpha());
    }
    const FVector ArrowAxis = (ArrowRestCM - AimTail).GetSafeNormal();
    FQuat TargetRotation = AimBowRotation.Quaternion();
    const FVector Axis = TargetRotation.RotateVector(ArrowAxis);
    const FVector RestFromAnchor = TargetRotation.RotateVector((ArrowRestCM - AimAnchor) * BowScale);
    const double AimDepth = CompoundAimDepthCM > 0. ? CompoundAimDepthCM : FMath::Max(200.f, RangeCM);
    const FVector TargetFromAnchor = FVector(AimDepth, 0., 0.) - TargetAnchor;
    const double Along = FVector::DotProduct(RestFromAnchor, Axis);
    const double Discriminant = FMath::Square(Along) + TargetFromAnchor.SizeSquared() - RestFromAnchor.SizeSquared();
    // The compound's drawing hand is fitted first. Correct any remainder about
    // the glass centre, including blends where the arm could not reach its contact.
    if ((!HasOpticalSight() || (CompoundOptic && CompoundAimDepthCM > 0.)) && !Axis.IsNearlyZero() && Discriminant > 0.)
    {
        // Keep the physical pin on screen centre while the real arrow axis
        // converges on the same aiming ray. Moving only a HUD dot is insufficient.
        const FVector RayPoint = RestFromAnchor + Axis * (-Along + FMath::Sqrt(Discriminant));
        TargetRotation = (FQuat::FindBetweenNormals(RayPoint.GetSafeNormal(), TargetFromAnchor.GetSafeNormal())
            * TargetRotation).GetNormalized();
    }
    // Keep the short release kick after the aiming correction.
    TargetRotation = (FRotator(.3f * Kick, .06f * Kick, 0.f).Quaternion() * TargetRotation).GetNormalized();
    const FQuat AimRotation = (TargetRotation * Mount.GetRotation().Inverse()).GetNormalized();
    const FVector TargetGrip = TargetAnchor - TargetRotation.RotateVector(AimAnchor * BowScale);
    const FVector AimLocation = TargetGrip - AimRotation.RotateVector(Mount.GetLocation());
    const float PoseAim = CompoundOptic ? FMath::SmoothStep(0.f, .82f, Aim) : Aim;
    FQuat Rotation = FQuat::Slerp(HipRotation, AimRotation, PoseAim).GetNormalized();
    // Interpolate the grip position as well as orientation, so the transition
    // rotates around the held bow instead of swinging it around the camera.
    const FVector AimGrip = AimRotation.RotateVector(GripLocation) + AimLocation;
    FVector HeldGrip = FMath::Lerp(HipGrip, AimGrip, PoseAim);
    if (CompoundOptic && bArrowNocked && PoseAim > 0.f && PoseAim < 1.f)
    {
        // Blend the seated nock in camera space. Rotating a drawn string around
        // the distant grip makes its near end sweep across the eye during ADS.
        const FVector GripToNock = Tail - GripLocation;
        const FVector HipNock = HipGrip + HipRotation.RotateVector(GripToNock);
        const FVector AimNock = AimGrip + AimRotation.RotateVector(GripToNock);
        HeldGrip = FMath::Lerp(HipNock, AimNock, PoseAim) - Rotation.RotateVector(GripToNock);
    }
    // Preserve the instantaneous grip motion when tension leaves the hand.
    // The limbs and the free string settle on shorter clocks than the wrist.
    float Tension = DrawMotionWeight();
    float Rebound = 0.f;
    if (ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < .28f)
    {
        const float T = ReleaseFeedbackAge;
        Tension += EndDrawMotionWeight * (1.f - FMath::SmoothStep(0.f, .075f, T));
        Rebound = ReleaseRatio * FeedbackScale * SwayAmplitudeCM * FMath::Lerp(1.f, .46f, Aim)
            * FMath::Sin(31.f * T) * FMath::Exp(-8.f * T) * (1.f - FMath::SmoothStep(.19f, .28f, T));
    }
    // Fade rigid sight motion to zero. Hand contact and free-string vibration have their own weights.
    Tension *= SightMotion;
    Rebound *= SightMotion;
    if (Tension > UE_SMALL_NUMBER || !FMath::IsNearlyZero(Rebound))
    {
        const float Lift = .65f * FMath::Sin(VisualTime * 6.1f) + .52f * FMath::Sin(VisualTime * 12.1f + .4f)
            + .16f * FMath::Sin(VisualTime * 25.9f);
        const float Roll = FMath::Sin(VisualTime * 9.4f) + .32f * FMath::Sin(VisualTime * 20.3f + .9f);
        const FRotator Response(.38f * Lift * Tension - 3.65f * Rebound,
            .15f * Roll * Tension, .53f * Roll * Tension + 2.65f * Rebound);
        Rotation = (Response.Quaternion() * Rotation).GetNormalized();
        HeldGrip += FVector(1.65f * Rebound, .19f * Roll * Tension, .27f * Lift * Tension - .55f * Rebound);
    }
    return FTransform(Rotation, HeldGrip - Rotation.RotateVector(GripLocation));
}

void UBowWeaponComponent::UpdateDoorPushPresentation()
{
    if (!Pivot) return;
    const auto* Pawn = Character.Get();
    const auto* DoorPush = Pawn ? Pawn->DoorPush.Get() : nullptr;
    const float Weight = DoorPush ? FMath::Clamp(DoorPush->GetPresentationWeight(), 0.f, 1.f) : 0.f;
    if (Weight > 0.f)
    {
        // Apply one camera-space rigid delta to the freshly sampled assembly.
        // The holding arm, bow parts, string and reserved arrow retain their
        // native contacts; the fallback fist never drives hand_l/bow_grip.
        const FTransform Base = Pivot->GetRelativeTransform();
        const FVector Grip = Base.TransformPosition(bHasGripMarker
            ? AnimatedRiserMount().GetLocation() : BowLocationCM);
        const FQuat LowerRotation = FRotator(-12.f * Weight, 0.f, -22.f * Weight).Quaternion();
        const FVector LowerOffset = FVector(-10.f, -8.f, -90.f) * Weight;
        Pivot->SetRelativeTransform(FTransform(
            (LowerRotation * Base.GetRotation()).GetNormalized(),
            Grip + LowerRotation.RotateVector(Base.GetLocation() - Grip) + LowerOffset,
            Base.GetScale3D()));
    }
    // Keep sampling even while completely below the view. HiddenInGame is a
    // render flag here, so socket geometry and the live recovery target keep
    // updating with the original clips instead of freezing on the entry pose.
    FPSComponentVisibility::SetHiddenInGameTree(Pivot,Weight >= 1.f - UE_KINDA_SMALL_NUMBER);
}

void UBowWeaponComponent::UpdateBowGeometry()
{
    // 弓体部件是挂点：它的局部空间就是锚点空间，弦与弦上箭作为子部件自动跟随。
    auto* Riser = Part(SlotRiser);
    if (Riser)
    {
        if (bHasGripMarker && Viewmodel->IsVisible())
        {
            Riser->SetRelativeTransform(AnimatedRiserMount());
        }
        else
        {
            // 数据表是基准，两个 cvar 只做实机叠加对点（默认 0），不写回 JSON。
            FVector Offset = FVector::ZeroVector, RotationText = FVector::ZeroVector;
            ReadVector3Text(CVarBowLocation.GetValueOnGameThread(), Offset);
            ReadVector3Text(CVarBowRotation.GetValueOnGameThread(), RotationText);
            const FRotator RotationOffset(RotationText.X, RotationText.Y, RotationText.Z);
            Riser->SetMount(BowLocationCM + GripTrimCM + Offset, (BowRotation + RotationOffset).Clamp(), BowScale);
        }
        Riser->SetPartVisible(Riser->HasMesh());
    }
    for (const FName& Slot : SlotOrder)
        if (Slot != SlotRiser && Slot != SlotString && Slot != SlotArrow)
            if (auto* Attachment = Part(Slot)) Attachment->SetPartVisible(Attachment->HasMesh());
    const FVector Nock = NockPoint();
    FVector Upper = UpperTipCM, Lower = LowerTipCM;
    if (Riser)
    {
        const bool Loaded = IsDrawing() || Stage == EBowStage::LetDown || Stage == EBowStage::Release || Stage == EBowStage::Recover
            || (Stage == EBowStage::DrawEntry && bEntryNeedsArrow && ReleaseFeedbackAge >= 0.f && ReleaseFeedbackAge < RingSeconds);
        Riser->ApplyStringLoad(Loaded ? Nock : BraceNockCM, BraceNockCM, FlexDistribution, -1.45f * ReleaseRing());
        Riser->FlexTips(Upper, Lower);
    }
    if (auto* BowString = Part(SlotString))
    {
        BowString->SetPartVisible(true);
        const auto* Echo=GetOwner()->FindComponentByClass<UBowMountainEchoComponent>();
        const auto* Cadence=GetOwner()->FindComponentByClass<UBowCadenceComponent>();
        const int32 Charges=Cadence&&Cadence->IsEquippedFor(InstanceId)?Cadence->ChargesFor(InstanceId):Echo?Echo->ChargesFor(InstanceId):0;
        if(!BowString->PoseString(Upper,Nock,Lower,Charges))
        {
            BowString->StretchRod(RodFor(SlotString, 0), Upper, Nock, StringRadiusCM);
            BowString->StretchRod(RodFor(SlotString, 1), Lower, Nock, StringRadiusCM);
        }
    }
    if (auto* ArrowRest = Part(SlotArrow))
    {
        const bool bEntryNock = Stage == EBowStage::DrawEntry && bEntryNeedsArrow;
        const float TakePhase = bEntryNock ? Elapsed / DrawEntrySeconds : Elapsed / NockSeconds;
        const bool bTakingArrow = (Stage == EBowStage::Nocking || bEntryNock) && TakePhase >= .34f;
        const bool bVisibleArrow = Stage != EBowStage::QuickCombat && (bArrowNocked || bTakingArrow);
        ArrowRest->SetPartVisible(bVisibleArrow);
        if (bVisibleArrow)
        {
            FVector Tail = Nock;
            FVector Axis = (ArrowRestCM - Tail).GetSafeNormal();
            if (bTakingArrow && bHasNockMarker && Viewmodel->IsVisible())
            {
                const FTransform Hand = Viewmodel->GetSocketTransform(TEXT("bow_nock"), RTS_Component) * Viewmodel->GetRelativeTransform();
                const FTransform Mount = AnimatedRiserMount();
                const FVector CarryTail = Mount.InverseTransformPosition(Hand.GetLocation());
                const bool bOrientedMarker = bEntryNock ? DrawEntryClip() != ClipDraw : bNockHasCarryAxis;
                const FVector CarryAxis = bOrientedMarker
                    ? Mount.InverseTransformVectorNoScale(Hand.GetRotation().GetForwardVector()).GetSafeNormal()
                    : (ArrowRestCM - CarryTail).GetSafeNormal();
                const float Seat = PickupSeatAlpha();
                const float AimedCarry = (CompoundAimDepthCM > 0. || UsesCompoundOptic()) ? AimAlpha() : 0.f;
                Tail = FMath::Lerp(CarryTail, Nock, Seat * (1.f - AimedCarry));
                const FVector RestAxis = (ArrowRestCM - Tail).GetSafeNormal();
                Axis = FMath::Lerp(CarryAxis, RestAxis, Seat).GetSafeNormal();
                if (AimedCarry > 0.f && bOrientedMarker && !RestAxis.IsNearlyZero())
                {
                    // Turn toward the groove during the carry, while the nock stays in the fingers.
                    const float ContactPhase = bEntryNock ? .90f : NockContactFraction;
                    const float Start = FMath::Min(.38f, ContactPhase);
                    const float Guide = FMath::SmoothStep(Start, ContactPhase, TakePhase);
                    // While the hand is still beside the bow, aiming from that moving
                    // point back at the groove would swing the arrow tip across the glass.
                    const FVector SeatedAxis = (ArrowRestCM - CompoundSightNock(BraceNockCM)).GetSafeNormal(UE_DOUBLE_SMALL_NUMBER, RestAxis);
                    const float AtGroove = FMath::SmoothStep(ContactPhase * .94f, ContactPhase, TakePhase);
                    const FVector GuideAxis = FMath::Lerp(SeatedAxis, RestAxis, AtGroove).GetSafeNormal();
                    const FQuat Turn = FQuat::FindBetweenNormals(CarryAxis, GuideAxis);
                    const FVector GuidedAxis = FQuat::Slerp(FQuat::Identity, Turn, Guide).RotateVector(CarryAxis);
                    Axis = FMath::Lerp(Axis, GuidedAxis, AimedCarry).GetSafeNormal();
                }
            }
            const FVector Tip = Tail + Axis * ArrowLengthCM;
            ArrowRest->StretchRod(RodFor(SlotArrow, 0), Tail, Tip, ArrowRadiusCM);
        }
    }
}

void UBowWeaponComponent::PlayClip(const TCHAR* Name, float Position, bool bLoop)
{
    UAnimSequence* Sequence = Animations.FindRef(FName(Name));
    if (!Sequence || !Viewmodel->GetSkeletalMeshAsset())
    {
        Viewmodel->SetVisibility(false);
        return;
    }
    const bool bLoadedCarry = bArrowNocked && bNockKeepsDrawPose;
    const bool bCarry = Stage == EBowStage::Ready;
    const float CarryWeight = bCarry ? GaitWeight * FMath::Lerp(1.f, .48f, CrouchProgress)
        * FMath::Lerp(1.f, .12f, AimAlpha()) * AimShakeScale() : 0.f;
    Viewmodel->SetLocomotion(
        Animations.FindRef(bLoadedCarry ? TEXT("LoadedWalk") : TEXT("Walk")),
        Animations.FindRef(bLoadedCarry ? TEXT("LoadedRun") : TEXT("Run")),
        GaitPhase, CarryWeight, SprintBlend, bCarry && bLoadedCarry, BraceNockCM);
    float ContactWeight=0.f;
    if(CastTransferAlpha<=0.f)
    {
        if(Stage==EBowStage::Drawing||Stage==EBowStage::Holding||Stage==EBowStage::LetDown)
            ContactWeight=1.f;
        else if(Stage==EBowStage::Nocking)
            ContactWeight=FMath::SmoothStep(.55f,NockContactFraction,Elapsed/FMath::Max(.001f,NockSeconds));
        else if(Stage==EBowStage::DrawEntry)
            ContactWeight=bEntryNeedsArrow?FMath::SmoothStep(.50f,.90f,Elapsed/FMath::Max(.001f,DrawEntrySeconds)):1.f;
    }
    Viewmodel->SetContactFitWeight(ContactWeight);
    // 与采集工具同一口径：只 PlayAnimation 一次，之后置零播放速率手动采样，
    // 否则每帧重新起播会让手臂停在片段开头。
    if (CurrentClip != Name)
    {
        // DrawEntry captured the exact start pose before its clock advanced.
        // Re-capturing here would restart the blend and miss the 0.2 s deadline.
        const bool bFromNockEntry = (Stage == EBowStage::Drawing || (Stage == EBowStage::Ready && bArrowNocked && bNockKeepsDrawPose)) &&
            (CurrentClip == TEXT("QuickNock") || CurrentClip == TEXT("ChainNock") || (CurrentClip == ClipNock && bNockKeepsDrawPose));
        if (!CurrentClip.IsNone() && !bFromNockEntry && Stage != EBowStage::DrawEntry && Stage != EBowStage::Nocking && Stage != EBowStage::QuickCombat && Stage != EBowStage::LetDown)
        {
            if (Stage == EBowStage::Release)
            {
                Viewmodel->CaptureRelease(ReleaseSeconds + RecoverSeconds);
                Viewmodel->AdvanceEntry(Elapsed);
            }
            else if (Stage == EBowStage::Drawing && CurrentClip == TEXT("LoadedIdle"))
                Viewmodel->CaptureCarry(.10f);
            else Viewmodel->CaptureEntry(.12f);
        }
        Viewmodel->PlayAnimation(Sequence, false);
        Viewmodel->SetPlayRate(0.f);
        CurrentClip = Name;
        if (Stage == EBowStage::Release)
        {
            Viewmodel->SetPosition(0.f, false);
            Viewmodel->TickAnimation(0.f, false);
            Viewmodel->RefreshBoneTransforms();
        }
    }
    const float Length = Sequence->GetPlayLength();
    if (Length <= KINDA_SMALL_NUMBER) { Viewmodel->SetVisibility(false); return; }
    bCurrentClipLoops=bLoop;
    Viewmodel->SetPosition(bLoop ? FMath::Fmod(Position, Length) : FMath::Clamp(Position, 0.f, Length), false);
    Viewmodel->TickAnimation(0.f, false);
    Viewmodel->RefreshBoneTransforms();
    Viewmodel->SetVisibility(true);
}

float UBowWeaponComponent::ClipLength(const TCHAR* Name) const
{
    const UAnimSequence* Sequence = Animations.FindRef(FName(Name));
    return Sequence ? Sequence->GetPlayLength() : 0.f;
}

void UBowWeaponComponent::SampleArms()
{
    SampleCompoundAimDepth();
    if (!bUsesArms) { Viewmodel->SetVisibility(false); return; }
    if(CastTransferAlpha>0.f){PlayClip(ClipIdle,VisualTime,true);return;}
    const auto Phase = [this](const TCHAR* Clip, float Fraction)
    { PlayClip(Clip, FMath::Clamp(Fraction, 0.f, 1.f) * ClipLength(Clip), false); };
    switch (Stage)
    {
    case EBowStage::QuickCombat:
        PlayClip(TEXT("QuickCombat"), Elapsed, false); break;
    case EBowStage::Equip:
        Phase(TEXT("Equip"), Elapsed / EquipSeconds); break;
    case EBowStage::Nocking:
        Phase(ClipNock, Elapsed / NockSeconds); break;
    case EBowStage::DrawEntry:
        if (const TCHAR* Entry = DrawEntryClip(); Entry != ClipDraw) Phase(Entry, Elapsed / DrawEntrySeconds);
        else Phase(ClipDraw, 0.f);
        break;
    case EBowStage::Drawing:
        Phase(ClipDraw, Elapsed / DrawSeconds); break;
    case EBowStage::LetDown:
        Phase(ClipDraw, LetDownPhase * (1.f - FMath::SmoothStep(0.f, 1.f, Elapsed / StageSeconds))); break;
    case EBowStage::Holding:
        if (ClipLength(ClipHold) > 0.f) PlayClip(ClipHold, HoldElapsed, true);
        else Phase(ClipDraw, 1.f);
        break;
    case EBowStage::Release:
        Phase(ClipRelease, Elapsed / (ReleaseSeconds + RecoverSeconds)); break;
    case EBowStage::Recover:
        Phase(ClipRelease, (ReleaseSeconds + Elapsed) / (ReleaseSeconds + RecoverSeconds)); break;
    default:
        if (bArrowNocked && bNockKeepsDrawPose)
        {
            if (ClipLength(TEXT("LoadedIdle")) > 0.f) PlayClip(TEXT("LoadedIdle"), VisualTime, true);
            else Phase(ClipDraw, 0.f);
        }
        else if (ClipLength(TEXT("Walk")) <= 0.f && !bArrowNocked && Character.IsValid() && Character->IsSprinting())
            PlayClip(TEXT("Run"), VisualTime, true);
        else PlayClip(bArrowNocked ? TEXT("Ready") : ClipIdle, VisualTime, true);
        break;
    }
}

