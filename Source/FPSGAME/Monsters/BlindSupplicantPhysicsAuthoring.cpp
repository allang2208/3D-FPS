#include "BlindSupplicantPhysicsAuthoring.h"

#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "Math/RotationMatrix.h"
#include "Misc/PackageName.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "UObject/Package.h"
#endif

namespace M07BodyPhysicsAuthoring
{
FString SerializeReceipt(const TSharedRef<FJsonObject>& Receipt)
{
    FString Result;
    FJsonSerializer::Serialize(Receipt, TJsonWriterFactory<>::Create(&Result));
    return Result;
}

#if WITH_EDITOR
struct FAnatomicalCapsule
{
    const TCHAR* Bone;
    const TCHAR* EndBone;
    float RadiusCm;
    float MassKg;
};

// Widths describe the slender 3.1 m source body. Capsule lengths and centers
// come from the actual imported reference pose, including its long limbs.
// Hands include the middle-finger chain without independent finger rigid bodies.
constexpr FAnatomicalCapsule Anatomy[] = {
    { TEXT("pelvis"), TEXT("spine_02"), 19.f, 14.f },
    { TEXT("spine_02"), TEXT("spine_05"), 18.f, 16.f },
    { TEXT("spine_05"), TEXT("neck_01"), 19.f, 12.f },
    { TEXT("head"), TEXT("neck_02"), 19.f, 8.f },
    { TEXT("upperarm_l"), TEXT("lowerarm_l"), 8.f, 4.f },
    { TEXT("upperarm_r"), TEXT("lowerarm_r"), 8.f, 4.f },
    { TEXT("lowerarm_l"), TEXT("hand_l"), 6.5f, 2.5f },
    { TEXT("lowerarm_r"), TEXT("hand_r"), 6.5f, 2.5f },
    { TEXT("hand_l"), TEXT("middle_03_l"), 5.5f, 1.2f },
    { TEXT("hand_r"), TEXT("middle_03_r"), 5.5f, 1.2f },
    { TEXT("thigh_l"), TEXT("calf_l"), 10.f, 8.f },
    { TEXT("thigh_r"), TEXT("calf_r"), 10.f, 8.f },
    { TEXT("calf_l"), TEXT("foot_l"), 7.f, 4.5f },
    { TEXT("calf_r"), TEXT("foot_r"), 7.f, 4.5f },
    { TEXT("foot_l"), TEXT("ball_l"), 6.f, 1.6f },
    { TEXT("foot_r"), TEXT("ball_r"), 6.f, 1.6f }
};

struct FReferenceCapsule
{
    FVector Center;
    FVector HalfAxis;
    double Radius;
};

FVector AngularLimits(const FName Bone)
{
    const FString Name = Bone.ToString();
    if (Name.StartsWith(TEXT("thigh"))) return FVector(55.f, 40.f, 25.f);
    if (Name.StartsWith(TEXT("calf"))) return FVector(70.f, 8.f, 8.f);
    if (Name.StartsWith(TEXT("hock"))) return FVector(55.f, 10.f, 10.f);
    if (Name.StartsWith(TEXT("upperarm"))) return FVector(75.f, 60.f, 45.f);
    if (Name.StartsWith(TEXT("lowerarm"))) return FVector(80.f, 10.f, 15.f);
    if (Name.StartsWith(TEXT("hand"))) return FVector(30.f, 25.f, 20.f);
    if (Name.StartsWith(TEXT("foot"))) return FVector(35.f, 18.f, 15.f);
    if (Name == TEXT("head")) return FVector(30.f, 25.f, 35.f);
    return FVector(22.f, 18.f, 15.f);
}
#endif
}

FString UBlindSupplicantPhysicsAuthoring::BuildBodyPhysics(USkeletalMesh* Mesh)
{
    const TSharedRef<FJsonObject> Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("success"), false);
    Receipt->SetBoolField(TEXT("saved"), false);
    const auto Fail = [&Receipt](const FString& Reason)
    {
        Receipt->SetStringField(TEXT("error"), Reason);
        return M07BodyPhysicsAuthoring::SerializeReceipt(Receipt);
    };

#if WITH_EDITOR
    if (!Mesh || !Mesh->GetPathName().StartsWith(TEXT("/Game/Monsters/BlindSupplicantM07/")))
    {
        return Fail(TEXT("Body physics authoring only accepts the M-07 mesh package."));
    }

    const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
    TArray<M07BodyPhysicsAuthoring::FAnatomicalCapsule> Anatomy;
    Anatomy.Append(M07BodyPhysicsAuthoring::Anatomy, UE_ARRAY_COUNT(M07BodyPhysicsAuthoring::Anatomy));
    for (const TCHAR* Side : {TEXT("l"), TEXT("r")})
    {
        const bool bLeft = FCString::Strcmp(Side, TEXT("l")) == 0;
        const TCHAR* Hock = bLeft ? TEXT("hock_l") : TEXT("hock_r");
        if (Ref.FindBoneIndex(Hock) == INDEX_NONE) continue;
        for (auto& Spec : Anatomy)
        {
            if (FName(Spec.Bone) == (bLeft ? TEXT("calf_l") : TEXT("calf_r"))) Spec.EndBone = Hock;
        }
        Anatomy.Add({Hock, bLeft ? TEXT("foot_l") : TEXT("foot_r"), 5.5f, 1.5f});
    }
    TArray<FTransform> ComponentFrames = Ref.GetRefBonePose();
    for (int32 Bone = 0; Bone < ComponentFrames.Num(); ++Bone)
    {
        const int32 Parent = Ref.GetParentIndex(Bone);
        if (Parent >= 0) ComponentFrames[Bone] *= ComponentFrames[Parent];
    }
    // Resolve the production body contract before changing an existing asset.
    // Gill bones are deliberately absent from this rigid-body specification.
    for (const auto& Spec : Anatomy)
    {
        if (Ref.FindBoneIndex(Spec.Bone) == INDEX_NONE || Ref.FindBoneIndex(Spec.EndBone) == INDEX_NONE)
        {
            return Fail(FString::Printf(TEXT("Required anatomical segment %s -> %s is absent."), Spec.Bone, Spec.EndBone));
        }
        if (ComponentFrames[Ref.FindBoneIndex(Spec.Bone)].GetScale3D().GetAbsMax() <= UE_SMALL_NUMBER)
        {
            return Fail(FString::Printf(TEXT("Bone %s has zero reference scale."), Spec.Bone));
        }
    }

    const bool bReferenceV04 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV04");
    const bool bReferenceV05 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV05");
    const bool bOriginalV06 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV06");
    const bool bOriginalV07 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV07");
    const bool bOriginalV08 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV08");
    const bool bOriginalV09 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV09");
    const bool bOriginalV11 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV11");
    const bool bOriginalV12 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12");
    const bool bOriginalV13 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13");
    const FString AssetName = bOriginalV13 ? TEXT("PA_M07_OriginalV13") : bOriginalV12 ? TEXT("PA_M07_OriginalV12") : bOriginalV11 ? TEXT("PA_M07_OriginalV11") : bOriginalV09 ? TEXT("PA_M07_OriginalV09") : bOriginalV08 ? TEXT("PA_M07_OriginalV08") : bOriginalV07 ? TEXT("PA_M07_OriginalV07") : bOriginalV06 ? TEXT("PA_M07_OriginalV06") : bReferenceV05 ? TEXT("PA_M07_V05") : bReferenceV04 ? TEXT("PA_M07_V04") : TEXT("PA_M07");
    const FString PackagePath = TEXT("/Game/Monsters/BlindSupplicantM07/") + AssetName;
    const FString ObjectPath = PackagePath + TEXT(".") + AssetName;
    UPhysicsAsset* Asset = FindObject<UPhysicsAsset>(nullptr, *ObjectPath);
    if (!Asset && FPackageName::DoesPackageExist(PackagePath))
    {
        Asset = LoadObject<UPhysicsAsset>(nullptr, *ObjectPath);
        if (!Asset) return Fail(TEXT("The existing PA_M07 package could not be loaded; it was left unchanged."));
    }
    bool bCreatedAsset = false;
    if (!Asset)
    {
        UPackage* Package = CreatePackage(*PackagePath);
        Asset = NewObject<UPhysicsAsset>(Package, FName(*AssetName), RF_Public | RF_Standalone | RF_Transactional);
        FAssetRegistryModule::AssetCreated(Asset);
        bCreatedAsset = true;
    }

    Asset->Modify();
    Asset->SkeletalBodySetups.Reset();
    Asset->ConstraintSetup.Reset();
    Asset->CollisionDisableTable.Reset();

    TArray<M07BodyPhysicsAuthoring::FReferenceCapsule> ReferenceCapsules;
    ReferenceCapsules.Reserve(Anatomy.Num());
    for (const auto& Spec : Anatomy)
    {
        const int32 BoneIndex = Ref.FindBoneIndex(Spec.Bone);
        const FTransform& BoneFrame = ComponentFrames[BoneIndex];
        FVector Start = BoneFrame.GetLocation();
        FVector End = ComponentFrames[Ref.FindBoneIndex(Spec.EndBone)].GetLocation();
        double CylinderLength = FMath::Max(0.0, FVector::Distance(Start, End) - 2.0 * Spec.RadiusCm);
        if (FName(Spec.Bone) == TEXT("head"))
        {
            // The head joint lies inside the sensory head. Extend its volume
            // along the neck-to-head axis rather than placing it in the neck.
            const FVector HeadAxis = (Start - End).GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
            End = Start + HeadAxis * 4.0;
            Start -= HeadAxis * 4.0;
            CylinderLength = 8.0;
        }
        const FVector Center = (Start + End) * 0.5;
        const FVector Axis = (End - Start).GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
        const double BoneScale = BoneFrame.GetScale3D().GetAbsMax();

        USkeletalBodySetup* Body = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
        Body->BoneName = Spec.Bone;
        Body->PhysicsType = PhysType_Default;
        Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        FKSphylElem Shape;
        Shape.Center = BoneFrame.InverseTransformPosition(Center);
        Shape.Rotation = FRotationMatrix::MakeFromZ(BoneFrame.InverseTransformVectorNoScale(Axis)).Rotator();
        Shape.Radius = Spec.RadiusCm / BoneScale;
        Shape.Length = CylinderLength / BoneScale;
        Body->AggGeom.SphylElems.Add(Shape);
        if (Body->BoneName == TEXT("spine_05"))
        {
            // This source has a wide shoulder span above a narrow rib cage.
            // Keep the clavicles inside the chest body instead of adding
            // tiny clavicle rigid bodies or inflating the entire torso.
            const FVector Left = ComponentFrames[Ref.FindBoneIndex(TEXT("upperarm_l"))].GetLocation();
            const FVector Right = ComponentFrames[Ref.FindBoneIndex(TEXT("upperarm_r"))].GetLocation();
            FKSphylElem Shoulders;
            Shoulders.Center = BoneFrame.InverseTransformPosition((Left + Right) * 0.5);
            Shoulders.Rotation = FRotationMatrix::MakeFromZ(BoneFrame.InverseTransformVectorNoScale(Left - Right)).Rotator();
            Shoulders.Radius = 9.5 / BoneScale;
            Shoulders.Length = FMath::Max(0.0, FVector::Distance(Left, Right) - 19.0) / BoneScale;
            Body->AggGeom.SphylElems.Add(Shoulders);
        }

        FBodyInstance& Instance = Body->DefaultInstance;
        Instance.SetCollisionProfileName(TEXT("Ragdoll"));
        // Keep the body shapes available to the existing visibility-channel
        // weapon queries while the character mesh is in QueryOnly mode.
        Instance.SetResponseToChannel(ECC_Visibility, ECR_Block);
        Instance.SetMassOverride(Spec.MassKg);
        Instance.LinearDamping = 0.8f;
        Instance.AngularDamping = 2.5f;
        Instance.bUseCCD = true;
        Instance.SetPositionSolverIterationCount(16);
        Instance.SetVelocitySolverIterationCount(8);
        Instance.SetMaxDepenetrationVelocity(150.f);
        Body->InvalidatePhysicsData();
        Body->CreatePhysicsMeshes();
        Asset->SkeletalBodySetups.Add(Body);
        ReferenceCapsules.Add({Center, Axis * CylinderLength * 0.5, Spec.RadiusCm});
    }
    Asset->UpdateBodySetupIndexMap();

    const FVector Across = (ComponentFrames[Ref.FindBoneIndex(TEXT("upperarm_l"))].GetLocation()
        - ComponentFrames[Ref.FindBoneIndex(TEXT("upperarm_r"))].GetLocation()).GetSafeNormal(UE_SMALL_NUMBER, FVector::RightVector);
    const FVector Upright = (ComponentFrames[Ref.FindBoneIndex(TEXT("spine_05"))].GetLocation()
        - ComponentFrames[Ref.FindBoneIndex(TEXT("pelvis"))].GetLocation()).GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
    const FVector Forward = FVector::CrossProduct(Across, Upright).GetSafeNormal(UE_SMALL_NUMBER, FVector::ForwardVector);
    for (int32 BodyIndex = 0; BodyIndex < Asset->SkeletalBodySetups.Num(); ++BodyIndex)
    {
        const FName BoneName = Asset->SkeletalBodySetups[BodyIndex]->BoneName;
        const int32 Bone = Ref.FindBoneIndex(BoneName);
        int32 Parent = Ref.GetParentIndex(Bone);
        while (Parent >= 0 && Asset->FindBodyIndex(Ref.GetBoneName(Parent)) == INDEX_NONE)
        {
            Parent = Ref.GetParentIndex(Parent);
        }
        if (Parent < 0) continue;

        const auto& Capsule = ReferenceCapsules[BodyIndex];
        FVector Shaft = Capsule.HalfAxis.GetSafeNormal();
        if (Shaft.IsNearlyZero()) Shaft = Upright;
        const FVector BendAxis = FMath::Abs(FVector::DotProduct(Shaft, Forward)) > 0.95 ? Upright : Forward;
        // A single component-space joint frame is expressed relative to both
        // bodies. X follows the child segment and swing 1 bends toward the
        // anatomical forward plane; elbow/knee swing 2 and twist stay narrow.
        const FTransform Anchor(FRotationMatrix::MakeFromXY(Shaft, BendAxis).ToQuat(), ComponentFrames[Bone].GetLocation());
        UPhysicsConstraintTemplate* Joint = NewObject<UPhysicsConstraintTemplate>(Asset, NAME_None, RF_Transactional);
        FConstraintInstance& Constraint = Joint->DefaultInstance;
        Constraint.JointName = BoneName;
        Constraint.ConstraintBone1 = BoneName;
        Constraint.ConstraintBone2 = Ref.GetBoneName(Parent);
        Constraint.SetRefFrame(EConstraintFrame::Frame1, Anchor.GetRelativeTransform(ComponentFrames[Bone]));
        Constraint.SetRefFrame(EConstraintFrame::Frame2, Anchor.GetRelativeTransform(ComponentFrames[Parent]));
        Constraint.SetLinearXLimit(LCM_Locked, 0.f);
        Constraint.SetLinearYLimit(LCM_Locked, 0.f);
        Constraint.SetLinearZLimit(LCM_Locked, 0.f);
        const FVector Limits = M07BodyPhysicsAuthoring::AngularLimits(BoneName);
        Constraint.SetAngularSwing1Limit(ACM_Limited, Limits.X);
        Constraint.SetAngularSwing2Limit(ACM_Limited, Limits.Y);
        Constraint.SetAngularTwistLimit(ACM_Limited, Limits.Z);
        Constraint.SetLinearBreakable(false, 0.f);
        Constraint.SetAngularBreakable(false, 0.f);
        Constraint.SetDisableCollision(true);
        Constraint.SetProjectionParams(true, 0.1f, 0.1f, 3.f, 15.f);
        Asset->ConstraintSetup.Add(Joint);
        Asset->DisableCollision(BodyIndex, Asset->FindBodyIndex(Constraint.ConstraintBone2));
    }

    // Anatomical volumes overlap at hips, shoulders and the torso. Suppress
    // these authored rest overlaps while retaining contacts between separated
    // limbs; this avoids an impulse from overlapping hit shapes at handoff.
    for (int32 A = 0; A < ReferenceCapsules.Num(); ++A)
    {
        for (int32 B = A + 1; B < ReferenceCapsules.Num(); ++B)
        {
            const auto& First = ReferenceCapsules[A];
            const auto& Second = ReferenceCapsules[B];
            FVector ClosestA, ClosestB;
            FMath::SegmentDistToSegmentSafe(First.Center - First.HalfAxis, First.Center + First.HalfAxis,
                Second.Center - Second.HalfAxis, Second.Center + Second.HalfAxis, ClosestA, ClosestB);
            if (FVector::DistSquared(ClosestA, ClosestB) < FMath::Square(First.Radius + Second.Radius))
            {
                Asset->DisableCollision(A, B);
            }
        }
    }

    Asset->UpdateBoundsBodiesArray();
    Asset->SetPreviewMesh(Mesh, false);
    Asset->MarkPackageDirty();
    Mesh->Modify();
    Mesh->SetPhysicsAsset(Asset);
    Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"), true);
    Receipt->SetBoolField(TEXT("created_asset"), bCreatedAsset);
    Receipt->SetBoolField(TEXT("caller_must_save_packages"), true);
    Receipt->SetStringField(TEXT("physics_asset"), Asset->GetPathName());
    Receipt->SetStringField(TEXT("mesh"), Mesh->GetPathName());
    Receipt->SetNumberField(TEXT("bodies"), Asset->SkeletalBodySetups.Num());
    Receipt->SetNumberField(TEXT("constraints"), Asset->ConstraintSetup.Num());
    return M07BodyPhysicsAuthoring::SerializeReceipt(Receipt);
#else
    return Fail(TEXT("M-07 body physics authoring requires an Editor target."));
#endif
}
