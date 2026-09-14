#include "FatZombie.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"

bool AFatZombie::PrepareCombatPhysics(USkeletalMesh* InMesh, bool bApply)
{
#if WITH_EDITOR
    if (!InMesh || !InMesh->GetPhysicsAsset()) return false;
    auto* Asset = InMesh->GetPhysicsAsset();
    const auto& Ref = InMesh->GetRefSkeleton();
    UE_LOG(LogTemp, Display, TEXT("FAT_PHYSICS_BEFORE asset=%s bodies=%d constraints=%d per_poly=%d"),
        *Asset->GetPathName(), Asset->SkeletalBodySetups.Num(), Asset->ConstraintSetup.Num(), InMesh->GetEnablePerPolyCollision());
    for (const USkeletalBodySetup* Body : Asset->SkeletalBodySetups)
    {
        if (!Body || Ref.FindBoneIndex(Body->BoneName) == INDEX_NONE) return false;
        UE_LOG(LogTemp, Display, TEXT("FAT_PHYSICS_BODY bone=%s trace_flag=%d resolved_trace=%d physics_type=%d shapes=%d"),
            *Body->BoneName.ToString(), int32(Body->CollisionTraceFlag), int32(Body->GetCollisionTraceFlag()), int32(Body->PhysicsType), Body->AggGeom.GetElementCount());
    }
    if (!bApply) return true;
    if (Ref.FindBoneIndex(TEXT("FatZombieRoot")) == INDEX_NONE || Ref.FindBoneIndex(TEXT("Hips")) == INDEX_NONE) return false;
    TArray<FTransform> Frames = Ref.GetRefBonePose();
    for (int32 I = 0; I < Frames.Num(); ++I)
        if (Ref.GetParentIndex(I) >= 0) Frames[I] = Frames[I] * Frames[Ref.GetParentIndex(I)];

    Asset->Modify();
    Asset->ConstraintSetup.Reset();
    Asset->CollisionDisableTable.Reset();
    if (Asset->FindBodyIndex(TEXT("FatZombieRoot")) == INDEX_NONE)
    {
        auto* Root = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
        Root->BoneName = TEXT("FatZombieRoot");
        FKSphereElem Sphere;
        Sphere.Radius = 1.f / Frames[Ref.FindBoneIndex(Root->BoneName)].GetScale3D().GetAbsMax();
        Root->AggGeom.SphereElems.Add(Sphere);
        Asset->SkeletalBodySetups.Insert(Root, 0);
    }
    const TMap<FName, float> Masses = {
        {TEXT("FatZombieRoot"),1}, {TEXT("Hips"),30}, {TEXT("Spine02"),30}, {TEXT("Spine01"),25}, {TEXT("Spine"),25},
        {TEXT("neck"),3}, {TEXT("Head"),10}, {TEXT("LeftArm"),7}, {TEXT("RightArm"),7},
        {TEXT("LeftForeArm"),4}, {TEXT("RightForeArm"),4}, {TEXT("LeftHand"),2}, {TEXT("RightHand"),2},
        {TEXT("LeftUpLeg"),14}, {TEXT("RightUpLeg"),14}, {TEXT("LeftLeg"),8}, {TEXT("RightLeg"),8},
        {TEXT("LeftFoot"),3}, {TEXT("RightFoot"),3}};
    for (USkeletalBodySetup* Body : Asset->SkeletalBodySetups)
    {
        Body->Modify();
        // Guns use complex Visibility rays; melee uses simple sweeps. Make the
        // same bone-local capsules available to BOTH, retaining head bone hits.
        Body->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        Body->PhysicsType = PhysType_Default;
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->DefaultInstance.LinearDamping = .8f;
        Body->DefaultInstance.AngularDamping = 2.5f;
        Body->DefaultInstance.SetMassOverride(Masses.FindRef(Body->BoneName));
        Body->DefaultInstance.bUseCCD = true;
        Body->DefaultInstance.PositionSolverIterationCount = 16;
        Body->DefaultInstance.VelocitySolverIterationCount = 8;
        if (Body->BoneName == TEXT("FatZombieRoot"))
        {
            Body->bConsiderForBounds = false;
            Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision);
        }
        Body->InvalidatePhysicsData();
        Body->CreatePhysicsMeshes();
    }
    Asset->UpdateBodySetupIndexMap();
    for (int32 I = 0; I < Asset->SkeletalBodySetups.Num(); ++I)
    {
        const FName Name = Asset->SkeletalBodySetups[I]->BoneName;
        const int32 Bone = Ref.FindBoneIndex(Name);
        int32 Parent = Ref.GetParentIndex(Bone);
        while (Parent >= 0 && Asset->FindBodyIndex(Ref.GetBoneName(Parent)) == INDEX_NONE) Parent = Ref.GetParentIndex(Parent);
        if (Parent < 0) continue;
        const FName ParentName = Ref.GetBoneName(Parent);
        auto* Joint = NewObject<UPhysicsConstraintTemplate>(Asset, NAME_None, RF_Transactional);
        auto& C = Joint->DefaultInstance;
        C.JointName = Name; C.ConstraintBone1 = Name; C.ConstraintBone2 = ParentName;
        // Both frames describe the same reference joint. Retain the inverse bone
        // scale: UE reapplies each body's imported scale when it creates joints.
        const FTransform Anchor(Frames[Bone].GetRotation(), Frames[Bone].GetLocation());
        C.SetRefFrame(EConstraintFrame::Frame1, Anchor.GetRelativeTransform(Frames[Bone]));
        C.SetRefFrame(EConstraintFrame::Frame2, Anchor.GetRelativeTransform(Frames[Parent]));
        C.SetLinearXLimit(LCM_Locked, 0); C.SetLinearYLimit(LCM_Locked, 0); C.SetLinearZLimit(LCM_Locked, 0);
        FVector Limits(20,20,15);
        const FString N = Name.ToString();
        if (N.Contains(TEXT("UpLeg"))) Limits = FVector(55,40,30);
        else if (N.EndsWith(TEXT("Leg"))) Limits = FVector(55,12,12);
        else if (N.Contains(TEXT("ForeArm"))) Limits = FVector(55,15,20);
        else if (N.EndsWith(TEXT("Arm"))) Limits = FVector(70,60,45);
        else if (N.Contains(TEXT("Hand"))) Limits = FVector(30,25,20);
        else if (N.Contains(TEXT("Foot"))) Limits = FVector(25,20,15);
        else if (Name == TEXT("Head") || Name == TEXT("neck")) Limits = FVector(25,30,30);
        const bool RootJoint = ParentName == TEXT("FatZombieRoot");
        C.SetAngularSwing1Limit(RootJoint ? ACM_Locked : ACM_Limited, Limits.X);
        C.SetAngularSwing2Limit(RootJoint ? ACM_Locked : ACM_Limited, Limits.Y);
        C.SetAngularTwistLimit(RootJoint ? ACM_Locked : ACM_Limited, Limits.Z);
        C.SetDisableCollision(true);
        Asset->ConstraintSetup.Add(Joint);
        Asset->DisableCollision(I, Asset->FindBodyIndex(ParentName));
    }
    // These fitted hit capsules overlap around the fat torso. Disable pairs that
    // already overlap in the reference pose; retain separated limb contacts.
    for (int32 I = 0; I < Asset->SkeletalBodySetups.Num(); ++I)
        for (int32 J = I+1; J < Asset->SkeletalBodySetups.Num(); ++J)
        {
            const USkeletalBodySetup* A = Asset->SkeletalBodySetups[I]; const USkeletalBodySetup* B = Asset->SkeletalBodySetups[J];
            bool Overlap = A->BoneName == TEXT("FatZombieRoot") || B->BoneName == TEXT("FatZombieRoot");
            const auto& TA = Frames[Ref.FindBoneIndex(A->BoneName)];
            const auto& TB = Frames[Ref.FindBoneIndex(B->BoneName)];
            for (const auto& CA : A->AggGeom.SphylElems) for (const auto& CB : B->AggGeom.SphylElems)
            {
                const FVector PA = TA.TransformPosition(CA.Center), PB = TB.TransformPosition(CB.Center);
                const double SA = TA.GetScale3D().GetAbsMax(), SB = TB.GetScale3D().GetAbsMax();
                const FVector DA = TA.TransformVectorNoScale(CA.Rotation.Quaternion().GetAxisZ()) * CA.Length * SA * .5;
                const FVector DB = TB.TransformVectorNoScale(CB.Rotation.Quaternion().GetAxisZ()) * CB.Length * SB * .5;
                FVector NearestA, NearestB;
                FMath::SegmentDistToSegmentSafe(PA-DA, PA+DA, PB-DB, PB+DB, NearestA, NearestB);
                Overlap |= FVector::DistSquared(NearestA,NearestB) < FMath::Square(CA.Radius*SA+CB.Radius*SB+1.);
            }
            if (Overlap) Asset->DisableCollision(I,J);
        }
    Asset->UpdateBoundsBodiesArray();
    Asset->MarkPackageDirty();
    UE_LOG(LogTemp, Display, TEXT("FAT_PHYSICS_PREPARED bodies=%d constraints=%d trace=SimpleAsComplex mass_kg=200"), Asset->SkeletalBodySetups.Num(), Asset->ConstraintSetup.Num());
    return true;
#else
    return false;
#endif
}
