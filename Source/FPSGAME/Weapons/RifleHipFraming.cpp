#include "RifleHipFraming.h"
#include "AKMSovietCalibration.h"
#include "WeaponGripProfile.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"

namespace RifleHipFraming
{
bool Supports(const FString& Definition)
{
    // Explicit scope: do not change either machine gun, including their grip families.
    return Definition == TEXT("ue_m4a1") || Definition == TEXT("ue_hk416")
        || Definition == TEXT("ue_qbz191") || Definition == TEXT("ue_akm")
        || Definition == TEXT("ue_m16a2") || Definition == TEXT("ue_ash12")
        || Definition == TEXT("ue_a762") || Definition == TEXT("ue_svd");
}

FVector PresentationOffset(const FString& Definition)
{
    // Camera-space centimetres, independent of the shared authoring basis.
    // Restore receiver/bolt detail cropped by forcing every wrist to M4 depth.
    // Move the gun and both arms together; ADS keeps its own sight calibration.
    float Forward = 0.f;
    if (Definition == TEXT("ue_qbz191") || Definition == TEXT("ue_m16a2")) Forward = 5.f;
    else if (Definition == TEXT("ue_akm") || Definition == TEXT("ue_a762")) Forward = 9.f;
    else if (Definition == TEXT("ue_ash12")) Forward = 8.f;
    else if (Definition == TEXT("ue_svd")) Forward = 10.f;
    return FVector(Forward, 0.f, 0.f);
}

bool SampleBone(const UAnimSequence& Idle, FName Bone, FTransform& Pose,const FWeaponGripClip* Layer)
{
    const FReferenceSkeleton& Ref = Idle.GetSkeleton()->GetReferenceSkeleton();
    int32 Index = Ref.FindBoneIndex(Bone);
    if (Index == INDEX_NONE) return false;
    Pose = FTransform::Identity;
    for (; Index != INDEX_NONE; Index = Ref.GetParentIndex(Index))
    {
        FTransform Local;
        Idle.GetBoneTransform(Local, FSkeletonPoseBoneIndex(Index), FAnimExtractContext(0.0, false), false);
        if(Layer)Layer->ApplyLocal(Ref.GetBoneName(Index),0.f,Local);
        Pose = Pose * Local;
    }
    return true;
}

bool SampleFrame(UAnimSequence* Idle, const FVector& Scale, bool bAKMSights,
    FVector& Hand, FQuat& AxisFrame,UWeaponGripProfile* Profile=nullptr)
{
    if (!Idle || !Idle->GetSkeleton()) return false;
    FTransform HandPose, RootPose, RearPose, FrontPose;
    const auto* Layer=Profile?Profile->Find(Idle):nullptr;
    if (!SampleBone(*Idle, TEXT("hand_r"), HandPose,Layer)
        || !SampleBone(*Idle, TEXT("WPN_root"), RootPose,Layer)
        || !SampleBone(*Idle, TEXT("WPN_RearSight"), RearPose,Layer)
        || !SampleBone(*Idle, TEXT("WPN_FrontSight"), FrontPose,Layer)) return false;

    const FVector Rear = bAKMSights ? RootPose.TransformPosition(AKMSoviet::Rear) : RearPose.GetLocation();
    const FVector Front = bAKMSights ? RootPose.TransformPosition(AKMSoviet::Front) : FrontPose.GetLocation();
    const FVector Axis = ((Front - Rear) * Scale).GetSafeNormal();
    const FVector Up = (RootPose.GetRotation().RotateVector(FVector::UpVector) * Scale).GetSafeNormal();
    Hand = HandPose.GetLocation() * Scale;
    if (Axis.IsNearlyZero() || (Axis ^ Up).IsNearlyZero() || Hand.ContainsNaN()) return false;
    AxisFrame = FRotationMatrix::MakeFromXZ(Axis, Up).ToQuat();
    return true;
}
}

void FRifleHipFraming::Initialize(const FString& Definition, UAnimSequence* Idle,
    const FVector& Anchor, const FRotator& BaseRotation, const FVector& Scale, bool bMeasuredAKMSights)
{
    *this = FRifleHipFraming();
    if (!RifleHipFraming::Supports(Definition)) return;

    // The accepted M4 idle is the common ruler. This load is only on weapon initialization,
    // never in the per-frame path, and does not add a mesh/animation asset dependency to LMGs.
    UAnimSequence* Reference = Definition == TEXT("ue_m4a1") ? Idle : LoadObject<UAnimSequence>(nullptr,
        TEXT("/Game/Weapons/M4ContactImpactFinal/A_AKM_idle.A_AKM_idle"));
    FVector Hand;
    FQuat Axis;
    if (!RifleHipFraming::SampleFrame(Reference, Scale, false, Hand, Axis)) return;
    MeshScale = Scale;
    bAKMSights = bMeasuredAKMSights;
    const FVector ReferenceHand = Anchor + BaseRotation.RotateVector(Hand);
    TargetHand = ReferenceHand + RifleHipFraming::PresentationOffset(Definition);
    TargetAxis = BaseRotation.Quaternion() * Axis;
    bReferenceReady = true;
    SelectIdle(Idle);
}

void FRifleHipFraming::SelectIdle(UAnimSequence* Idle,UWeaponGripProfile* Profile)
{
    if (!bReferenceReady || (SampledIdle.Get() == Idle && SampledProfile.Get() == Profile)) return;
    SampledIdle = Idle;
    SampledProfile = Profile;
    bReady = false;
    FVector Hand;
    FQuat Axis;
    if (!RifleHipFraming::SampleFrame(Idle, MeshScale, bAKMSights, Hand, Axis,Profile)) return;

    // Rigid movement of gun AND arms: common weapon axis and a per-rifle wrist depth.
    // The presentation offset is included once in TargetHand, not accumulated on grip changes.
    // Keep the model scale, each grip's contacts and all authored animation motion intact.
    HipRotation = (TargetAxis * Axis.Inverse()).GetNormalized();
    HipLocation = TargetHand - HipRotation.RotateVector(Hand);
    bReady = true;
}
