#include "PKMCarryHandleDynamics.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

void FPKMCarryHandleDynamics::Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose)
{
    auto* Asset = Mesh.GetSkeletalMeshAsset();
    if (!Asset) return;
    const auto& Ref = Asset->GetRefSkeleton();
    if (SourceMesh.Get() != Asset || BoneCount != Ref.GetNum())
    {
        SourceMesh = Asset;
        BoneCount = Ref.GetNum();
        BoneIndex = Ref.FindBoneIndex(TEXT("PKM_CarryHandle"));
        ParentIndex = BoneIndex != INDEX_NONE ? Ref.GetParentIndex(BoneIndex) : INDEX_NONE;
        if (BoneIndex != INDEX_NONE) BindLocal = Ref.GetRefBonePose()[BoneIndex];
        LastTime = -1.;
        Angle = AngularSpeed = 0.f;
    }
    if (!Pose.IsValidIndex(BoneIndex) || !Pose.IsValidIndex(ParentIndex)) return;

    // Existing clips have no handle track: reconstruct its mount from the
    // parent every evaluation, including repeated evaluations in the same tick.
    const FTransform Mount = BindLocal * Pose[ParentIndex];
    Pose[BoneIndex] = Mount;
    const auto* World = Mesh.GetWorld();
    if (!World || !World->IsGameWorld() || !Mesh.IsVisible() || Mesh.bHiddenInGame)
    {
        LastTime = -1.;
        Angle = AngularSpeed = 0.f;
        return;
    }

    const FTransform ParentWorld = Pose[ParentIndex] * Mesh.GetComponentTransform();
    const FVector Position = (Mount * Mesh.GetComponentTransform()).GetLocation();
    const FQuat Rotation = ParentWorld.GetRotation();
    const double Now = World->GetTimeSeconds();
    const double Elapsed = Now - LastTime;
    // Switching/equipping and time discontinuities start from the detent rather
    // than converting a teleported camera or a long pause into an impact.
    if (LastTime < 0. || Elapsed < 0. || Elapsed > .25 ||
        (Position - LastPosition).SizeSquared() > FMath::Square(80.) ||
        Rotation.AngularDistance(LastRotation) > 1.2)
    {
        LastTime = Now;
        LastPosition = Position;
        LastRotation = Rotation;
        LastVelocity = LastAngularVelocity = FVector::ZeroVector;
        Acceleration = AngularAcceleration = FVector::ZeroVector;
        Angle = AngularSpeed = 0.f;
    }
    else if (Elapsed > UE_SMALL_NUMBER)
    {
        const FVector Velocity = (Position - LastPosition) / Elapsed;
        FQuat Delta = Rotation * LastRotation.Inverse();
        Delta.Normalize();
        FVector SpinAxis;
        double SpinAngle;
        Delta.ToAxisAndAngle(SpinAxis, SpinAngle);
        if (SpinAngle > UE_PI) SpinAngle -= 2. * UE_PI;
        const FVector SpinVelocity = SpinAxis * (SpinAngle / Elapsed);
        // Slower input filter: small aiming motions and hand tremor used to
        // reach the hinge almost unfiltered and show up as constant rocking.
        const float Filter = 1.f - FMath::Exp(-8.f * static_cast<float>(Elapsed));
        Acceleration = FMath::Lerp(Acceleration,
            ((Velocity - LastVelocity) / Elapsed).GetClampedToMaxSize(12000.), Filter);
        AngularAcceleration = FMath::Lerp(AngularAcceleration,
            ((SpinVelocity - LastAngularVelocity) / Elapsed).GetClampedToMaxSize(200.), Filter);

        // Source Y runs along the hinge; FBX reflects it in the WPN_root frame.
        // The lever is the existing wood's centroid from CarryHandle18, in cm,
        // with its axial component removed. No imported bone scale is reapplied.
        const FVector Axis = ParentWorld.TransformVectorNoScale(FVector(0., -1., 0.)).GetSafeNormal();
        const FVector RestLever = ParentWorld.TransformVectorNoScale(FVector(4.695156, 0., 3.939710));
        // Sensitivity pass 3: walking, aiming and hand tremor are below the
        // dead zone and move the hinge exactly zero. Above it the threshold is
        // subtracted before the gain, so the ramp in stays continuous and only
        // sharp events (sprint start/stop, landings, reload and fire impacts)
        // drive the lever. Set both thresholds to 0 to restore a plain gain.
        constexpr float LinearDeadZone = 250.f;
        constexpr float AngularDeadZone = 2.5f;
        constexpr float LinearGain = .10f;
        constexpr float AngularGain = .15f;
        const float LinearAmount = Acceleration.Size();
        const float AngularAmount = AngularAcceleration.Size();
        const float LinearDrive = FMath::Max(0.f, LinearAmount - LinearDeadZone) / FMath::Max(1.f, LinearAmount);
        const float AngularDrive = FMath::Max(0.f, AngularAmount - AngularDeadZone) / FMath::Max(1.f, AngularAmount);
        // Gravity stays the resting hang, at half its previous coupling so
        // tilting the weapon no longer swings the wood through its travel.
        const FVector ForceAcceleration = FVector(0., 0., World->GetGravityZ() * .12f) - Acceleration * (LinearGain * LinearDrive);
        constexpr float Frequency = 2.15f;
        constexpr float Omega = 2.f * PI * Frequency;
        constexpr float DampingRatio = .55f;
        constexpr float MinAngle = -10.f * PI / 180.f;
        constexpr float MaxAngle = 12.f * PI / 180.f;
        constexpr float SoftZone = 3.f * PI / 180.f;
        const double Duration = FMath::Min(Elapsed,.06);
        const int32 Steps = FMath::Max(1, FMath::CeilToInt(Duration * 240.));
        const float Dt = static_cast<float>(Duration / Steps);
        for (int32 Step = 0; Step < Steps; ++Step)
        {
            const FVector Lever = FQuat(Axis, Angle).RotateVector(RestLever);
            const double Inertia = FVector::DotProduct(Axis, FVector::CrossProduct(Lever, ForceAcceleration))
                / FMath::Max(1., Lever.SizeSquared())
                - AngularGain * AngularDrive * FVector::DotProduct(Axis, AngularAcceleration);
            const float Torque = FMath::Clamp(static_cast<float>(Inertia), -180.f, 180.f);
            // A soft stop progressively catches the handle before the hard
            // limit. Low restitution: the stop should not throw it back into
            // another visible rock.
            const float Stop = 1800.f*(FMath::Max(0.f,MinAngle+SoftZone-Angle)
                - FMath::Max(0.f,Angle-(MaxAngle-SoftZone)));
            AngularSpeed += (Torque + Stop - Omega * Omega * Angle - 2.f * DampingRatio * Omega * AngularSpeed) * Dt;
            Angle += AngularSpeed * Dt;
            if (Angle < MinAngle) { Angle = MinAngle; if (AngularSpeed<0.f) AngularSpeed *= -.08f; }
            if (Angle > MaxAngle) { Angle = MaxAngle; if (AngularSpeed>0.f) AngularSpeed *= -.08f; }
        }
        LastTime = Now;
        LastPosition = Position;
        LastRotation = Rotation;
        LastVelocity = Velocity;
        LastAngularVelocity = SpinVelocity;
    }
    const FVector ComponentAxis = Pose[ParentIndex].TransformVectorNoScale(FVector(0., -1., 0.)).GetSafeNormal();
    Pose[BoneIndex].SetRotation((FQuat(ComponentAxis, Angle) * Mount.GetRotation()).GetNormalized());
}
