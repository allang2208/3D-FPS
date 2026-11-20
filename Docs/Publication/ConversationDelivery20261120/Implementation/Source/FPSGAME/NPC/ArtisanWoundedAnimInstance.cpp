#include "ArtisanWoundedAnimInstance.h"

#include "Animation/AnimSingleNodeInstanceProxy.h"
#include "BonePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "ReferenceSkeleton.h"
#include "TwoBoneIK.h"

namespace ArtisanKneel
{
using FBone = FCompactPoseBoneIndex;
using FBodyPose = FCSPose<FCompactPose>;

FBone Find(const FBoneContainer& Bones, FName Name)
{
    const int32 Index = Bones.GetPoseBoneIndexForBoneName(Name);
    return Index == INDEX_NONE ? FBone(INDEX_NONE) : Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Index));
}

void Place(FBodyPose& Pose, FBone Bone, const FTransform& Position)
{
    const FBoneTransform Change(Bone, Position);
    Pose.LocalBlendCSBoneTransforms(MakeArrayView(&Change, 1), 1.f);
}

void Tilt(FBodyPose& Pose, FBone Bone, const FQuat& Rotation)
{
    if (Bone == INDEX_NONE) return;
    FTransform Part = Pose.GetComponentSpaceTransform(Bone);
    Part.SetRotation((Rotation * Part.GetRotation()).GetNormalized());
    Place(Pose, Bone, Part);
}

struct FLimb
{
    FBone Root{INDEX_NONE}, Joint{INDEX_NONE}, End{INDEX_NONE};

    void Bind(const FBoneContainer& Bones, FName Tip)
    {
        End = Find(Bones, Tip);
        Joint = End != INDEX_NONE ? Bones.GetParentBoneIndex(End) : FBone(INDEX_NONE);
        Root = Joint != INDEX_NONE ? Bones.GetParentBoneIndex(Joint) : FBone(INDEX_NONE);
    }

    void Reach(FBodyPose& Pose, const FVector& Target, const FVector& Pole, const FQuat& TipRotation) const
    {
        if (Root == INDEX_NONE) return;
        FTransform Upper = Pose.GetComponentSpaceTransform(Root);
        FTransform Lower = Pose.GetComponentSpaceTransform(Joint);
        FTransform Tip = Pose.GetComponentSpaceTransform(End);
        AnimationCore::SolveTwoBoneIK(Upper, Lower, Tip, Pole, Target, false, 1., 1.);
        Tip.SetRotation(TipRotation);
        const FBoneTransform Changes[] = {{Root, Upper}, {Joint, Lower}, {End, Tip}};
        Pose.LocalBlendCSBoneTransforms(Changes, 1.f);
    }
};

struct FHand
{
    FLimb Arm;
    FQuat PalmToWrist = FQuat::Identity;

    void Bind(const FBoneContainer& Bones, bool bRight)
    {
        const FName Wrist = bRight ? TEXT("hand_r") : TEXT("hand_l");
        Arm.Bind(Bones, Wrist);
        // Use the full bind skeleton here even when a distant mesh LOD drops its fingers.
        const auto& Ref = Bones.GetReferenceSkeleton();
        const int32 Hand = Ref.FindBoneIndex(Wrist);
        const int32 Index = Ref.FindBoneIndex(bRight ? TEXT("index_01_r") : TEXT("index_01_l"));
        const int32 Middle = Ref.FindBoneIndex(bRight ? TEXT("middle_01_r") : TEXT("middle_01_l"));
        const int32 Pinky = Ref.FindBoneIndex(bRight ? TEXT("pinky_01_r") : TEXT("pinky_01_l"));
        if (Hand == INDEX_NONE || Index == INDEX_NONE || Middle == INDEX_NONE || Pinky == INDEX_NONE) return;
        const FTransform HandBind = Ref.GetBoneAbsoluteTransform(Hand);
        const FVector Origin = HandBind.GetLocation();
        FVector Palm = (Ref.GetBoneAbsoluteTransform(Index).GetLocation() - Origin)
            ^ (Ref.GetBoneAbsoluteTransform(Pinky).GetLocation() - Origin);
        if (bRight) Palm = -Palm;
        const FVector Fingers = Ref.GetBoneAbsoluteTransform(Middle).GetLocation() - Origin;
        PalmToWrist = (FRotationMatrix::MakeFromXZ(Fingers, Palm).ToQuat().Inverse() * HandBind.GetRotation()).GetNormalized();
    }

    FQuat Facing(const FVector& Fingers, const FVector& Palm) const
    {
        return (FRotationMatrix::MakeFromXZ(Fingers, Palm).ToQuat() * PalmToWrist).GetNormalized();
    }
};

struct FGroundFinger
{
    FBone Joints[3] = {FBone(INDEX_NONE), FBone(INDEX_NONE), FBone(INDEX_NONE)};

    void RestOn(FBodyPose& Pose, const FVector& Ground, const FVector& Up, double Scale) const
    {
        for (int32 I = 0; I < 2; ++I)
        {
            if (Joints[I] == INDEX_NONE || Joints[I + 1] == INDEX_NONE) break;
            const FVector Joint = Pose.GetComponentSpaceTransform(Joints[I]).GetLocation();
            const FVector Segment = Pose.GetComponentSpaceTransform(Joints[I + 1]).GetLocation() - Joint;
            const double Length = Segment.Size();
            if (Length < UE_SMALL_NUMBER) continue;
            const FVector Along = FVector::VectorPlaneProject(Segment, Up).GetSafeNormal();
            if (Along.IsNearlyZero()) continue;
            const double Drop = FMath::Clamp((I == 0 ? 1.6 : 1.0) * Scale - ((Joint - Ground) | Up),
                                             -.65 * Length, .35 * Length);
            const FVector To = Along * FMath::Sqrt(Length * Length - Drop * Drop) + Up * Drop;
            Tilt(Pose, Joints[I], FQuat::FindBetweenNormals(Segment / Length, To / Length));
        }
    }
};

struct FWoundedProxy final : FAnimSingleNodeInstanceProxy
{
    explicit FWoundedProxy(UAnimInstance* Owner) : FAnimSingleNodeInstanceProxy(Owner) {}

    FLimb RightLeg, LeftLeg;
    FHand RightHand, LeftHand;
    FGroundFinger Fingers[5];
    FBone Pelvis{INDEX_NONE}, LowerSpine{INDEX_NONE}, UpperSpine{INDEX_NONE}, Neck{INDEX_NONE}, Toes{INDEX_NONE};
    int32 RigSerial = INDEX_NONE;
    FVector Floor = FVector::ZeroVector, FloorUp = FVector::UpVector;
    float Elapsed = 0.f, NextGroundSample = 0.f;

    virtual void PreUpdate(UAnimInstance* Anim, float Seconds) override
    {
        FAnimSingleNodeInstanceProxy::PreUpdate(Anim, Seconds);
        Elapsed += FMath::Max(Seconds, 0.f);
        if (Elapsed < NextGroundSample) return;
        NextGroundSample = Elapsed + .25f;
        USkeletalMeshComponent* Mesh = Anim->GetSkelMeshComponent();
        if (!Mesh || !Mesh->GetWorld()) return;
        const FTransform Frame = Mesh->GetComponentTransform();
        const FVector Base = Frame.GetLocation();
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(ArtisanKneelGround), false, Mesh->GetOwner());
        FCollisionObjectQueryParams GroundTypes(ECC_WorldStatic);
        GroundTypes.AddObjectTypesToQuery(ECC_WorldDynamic);
        FHitResult Hit;
        Floor = FVector::ZeroVector;
        FloorUp = FVector::UpVector;
        if (Mesh->GetWorld()->LineTraceSingleByObjectType(Hit, Base + FVector(0,0,15), Base - FVector(0,0,35),
                GroundTypes, Query) && Hit.ImpactNormal.Z > .65)
        {
            Floor = Frame.InverseTransformPosition(Hit.ImpactPoint);
            FloorUp = Frame.InverseTransformVectorNoScale(Hit.ImpactNormal).GetSafeNormal();
        }
    }

    void Bind(const FBoneContainer& Bones)
    {
        RigSerial = Bones.GetSerialNumber();
        Pelvis = Find(Bones, TEXT("pelvis"));
        LowerSpine = Find(Bones, TEXT("spine_01"));
        UpperSpine = Find(Bones, TEXT("spine_03"));
        Neck = Find(Bones, TEXT("neck_01"));
        Toes = Find(Bones, TEXT("ball_r"));
        RightLeg.Bind(Bones, TEXT("foot_r"));
        LeftLeg.Bind(Bones, TEXT("foot_l"));
        RightHand.Bind(Bones, true);
        LeftHand.Bind(Bones, false);
        const TCHAR* Digits[] = {TEXT("thumb"), TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")};
        for (int32 Digit = 0; Digit < UE_ARRAY_COUNT(Digits); ++Digit)
            for (int32 Joint = 0; Joint < 3; ++Joint)
                Fingers[Digit].Joints[Joint] = Find(Bones, *FString::Printf(TEXT("%s_0%d_r"), Digits[Digit], Joint + 1));
    }

    virtual bool Evaluate(FPoseContext& Output) override
    {
        FAnimSingleNodeInstanceProxy::Evaluate(Output);
        const FBoneContainer& Bones = Output.Pose.GetBoneContainer();
        if (RigSerial != Bones.GetSerialNumber()) Bind(Bones);
        if (Pelvis == INDEX_NONE || LeftLeg.Root == INDEX_NONE || RightLeg.Root == INDEX_NONE) return true;

        FBodyPose Pose;
        Pose.InitPose(Output.Pose);
        auto At = [&Pose](FBone Bone){ return Pose.GetComponentSpaceTransform(Bone).GetLocation(); };
        const FVector Up = FloorUp;
        const FVector Right = FVector::VectorPlaneProject(At(RightLeg.Root) - At(LeftLeg.Root), Up).GetSafeNormal();
        const FVector Front = (Right ^ Up).GetSafeNormal();
        if (Front.IsNearlyZero()) return true;
        auto OnFloor = [&](const FVector& Point){ return FVector::PointPlaneProject(Point, Floor, Up); };
        auto Lean = [&](double Degrees){ return FQuat(Right, FMath::DegreesToRadians(Degrees)); };

        const FVector HipStart = At(RightLeg.Root);
        const double Thigh = FVector::Distance(HipStart, At(RightLeg.Joint));
        const double Shin = FVector::Distance(At(RightLeg.Joint), At(RightLeg.End));
        const double Size = Thigh / 39.;
        const FTransform BackFoot = Pose.GetComponentSpaceTransform(RightLeg.End);
        const FTransform FrontFoot = Pose.GetComponentSpaceTransform(LeftLeg.End);
        const FVector ToeDirection = Toes != INDEX_NONE ? (At(Toes) - BackFoot.GetLocation()).GetSafeNormal()
                                                      : (Front - .55 * Up).GetSafeNormal();
        const FQuat Slope = FQuat::FindBetweenNormals(FVector::UpVector, Up);
        const FVector NearHip = OnFloor(HipStart) + Up * (5.2 * Size + .69 * Thigh);
        const FVector GroundKnee = OnFloor(HipStart) + Front * (.724 * Thigh) + Up * (5.2 * Size);
        // Placing the ankle from the contact knee and the actual shin length gives a folded
        // leg on the floor without changing either bone length or pushing the back boot through it.
        const double HeelRise = 4.8 * Size;
        const FVector BackAnkle = GroundKnee - Front * FMath::Sqrt(FMath::Max(0., Shin * Shin - HeelRise * HeelRise)) + Up * HeelRise;
        const FVector FrontAnkle = OnFloor(At(LeftLeg.Root)) + Front * (.91 * Thigh) - Right * (5.0 * Size)
            + Up * FMath::Clamp(FrontFoot.GetLocation().Z, 6. * Size, 12. * Size);

        FTransform Hips = Pose.GetComponentSpaceTransform(Pelvis);
        const FVector Socket = Hips.InverseTransformPosition(HipStart);
        const FQuat SideLean(Front, FMath::DegreesToRadians(-13.));
        Hips.SetRotation((SideLean * Lean(48.) * Slope * Hips.GetRotation()).GetNormalized());
        Hips.AddToTranslation(NearHip - Hips.TransformPosition(Socket));
        Place(Pose, Pelvis, Hips);
        const FQuat Boot = FQuat::FindBetweenNormals(ToeDirection, (-Front - .38 * Up).GetSafeNormal());
        RightLeg.Reach(Pose, BackAnkle, GroundKnee, (Boot * BackFoot.GetRotation()).GetNormalized());
        LeftLeg.Reach(Pose, FrontAnkle, NearHip + Front * 85. * Size - Right * 35. * Size,
                      (Slope * FrontFoot.GetRotation()).GetNormalized());
        const FVector Knee = At(LeftLeg.Joint);
        const FVector Palm = OnFloor(GroundKnee) + Front * (17. * Size) + Right * (10. * Size) + Up * (3.6 * Size);

        const double Breath = FMath::Sin(Elapsed * 1.65);
        Tilt(Pose, LowerSpine, Lean(14. + 1.1 * Breath));
        Tilt(Pose, UpperSpine, Lean(8. + .65 * Breath));
        Tilt(Pose, Neck, Lean(-18. + .9 * Breath));
        if (RightHand.Arm.Root != INDEX_NONE && LowerSpine != INDEX_NONE)
        {
            // Short arms must reach the floor with some bend left at the elbow. Lower the
            // shoulder along the torso's natural arc rather than stretching the forearm.
            const FVector Shoulder = At(RightHand.Arm.Root);
            const double Reach = .97 * (FVector::Distance(Shoulder, At(RightHand.Arm.Joint))
                + FVector::Distance(At(RightHand.Arm.Joint), At(RightHand.Arm.End)));
            const FVector Radial = Shoulder - At(LowerSpine);
            const double Run = FVector::VectorPlaneProject(Shoulder - Palm, Up).Size();
            const double MaxHeight = FMath::Sqrt(FMath::Max(0., Reach * Reach - Run * Run));
            const double Excess = ((Shoulder - Palm) | Up) - MaxHeight;
            if (Excess > 0. && !Radial.IsNearlyZero())
            {
                const double LowerHeight = FMath::Clamp((Radial | Up) - Excess, -Radial.Size(), Radial.Size());
                const FVector To = FVector::VectorPlaneProject(Radial, Up).GetSafeNormal()
                    * FMath::Sqrt(FMath::Max(0., Radial.SizeSquared() - LowerHeight * LowerHeight)) + Up * LowerHeight;
                Tilt(Pose, LowerSpine, FQuat::FindBetweenNormals(Radial.GetSafeNormal(), To.GetSafeNormal()));
            }
            RightHand.Arm.Reach(Pose, Palm, At(RightHand.Arm.Root) + (Right * 29. - Front * 15.) * Size,
                                RightHand.Facing(Front + .12 * Right, -Up));
            for (const FGroundFinger& Finger : Fingers) Finger.RestOn(Pose, Floor, Up, Size);
        }
        if (LeftHand.Arm.Root != INDEX_NONE)
        {
            const FVector Rest = Knee + (Up * 6. - Front * 4. - Right) * Size;
            LeftHand.Arm.Reach(Pose, Rest, At(LeftHand.Arm.Root) - (Right * 31. + Front * 11.) * Size,
                               LeftHand.Facing(Front + .22 * Right - .28 * Up, -Up));
        }
        const float Weight = FMath::SmoothStep(0.f, .48f, Elapsed);
        FCompactPose Before;
        if (Weight < 1.f) Before.CopyBonesFrom(Output.Pose);
        FBodyPose::ConvertComponentPosesToLocalPosesSafe(Pose, Output.Pose);
        if (Weight < 1.f)
        {
            for (FBone Bone : Output.Pose.ForEachBoneIndex())
            {
                const FTransform Kneeling = Output.Pose[Bone];
                Output.Pose[Bone].Blend(Before[Bone], Kneeling, Weight);
            }
        }
        return true;
    }
};
}

FAnimInstanceProxy* UArtisanWoundedAnimInstance::CreateAnimInstanceProxy()
{
    return new ArtisanKneel::FWoundedProxy(this);
}
