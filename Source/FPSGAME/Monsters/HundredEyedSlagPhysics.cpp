#include "HundredEyedSlagMonster.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Misc/PackageName.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

UPhysicsAsset* AHundredEyedSlagMonster::BuildFittedPhysicsAsset(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
    if (!InMesh || !InMesh->GetImportedModel() || InMesh->GetImportedModel()->LODModels.IsEmpty()) return nullptr;
    const FName Names[] = {TEXT("pelvis"), TEXT("spine"), TEXT("chest"), TEXT("carapace"),
        TEXT("front_upper_R"), TEXT("front_lower_R"), TEXT("front_palm_R"),
        TEXT("front_upper_L"), TEXT("front_lower_L"), TEXT("front_palm_L"),
        TEXT("rear_upper_L"), TEXT("rear_lower_L"), TEXT("rear_palm_L"),
        TEXT("rear_upper_R"), TEXT("rear_lower_R"), TEXT("rear_palm_R")};
    const float Masses[] = {20, 18, 16, 12, 6, 4, 3, 3, 2, 1.5f, 4, 2.5f, 1.5f, 4, 2.5f, 1.5f};
    const auto& Ref = InMesh->GetRefSkeleton();
    TArray<FTransform> Frames = Ref.GetRefBonePose();
    for (int32 I = 0; I < Frames.Num(); ++I)
        if (Ref.GetParentIndex(I) >= 0) Frames[I] = Frames[I] * Frames[Ref.GetParentIndex(I)];
    TArray<int32> BoneToBody; BoneToBody.Init(INDEX_NONE, Ref.GetNum());
    for (int32 I = 0; I < UE_ARRAY_COUNT(Names); ++I)
    {
        const int32 Bone = Ref.FindBoneIndex(Names[I]); if (Bone == INDEX_NONE) return nullptr;
        BoneToBody[Bone] = I;
    }
    for (int32 Bone = 0; Bone < Ref.GetNum(); ++Bone)
        if (BoneToBody[Bone] == INDEX_NONE && Ref.GetParentIndex(Bone) >= 0)
            BoneToBody[Bone] = BoneToBody[Ref.GetParentIndex(Bone)];
    TArray<TArray<FVector>> Points; Points.SetNum(UE_ARRAY_COUNT(Names));
    for (const auto& Section : InMesh->GetImportedModel()->LODModels[0].Sections)
        for (int32 V = 0; V < Section.SoftVertices.Num(); V += 4)
        {
            const auto& Vertex = Section.SoftVertices[V]; int32 Influence = 0;
            for (int32 J = 1; J < MAX_TOTAL_INFLUENCES; ++J)
                if (Vertex.InfluenceWeights[J] > Vertex.InfluenceWeights[Influence]) Influence = J;
            const int32 Bone = Section.BoneMap[Vertex.InfluenceBones[Influence]];
            const int32 Region = BoneToBody[Bone];
            if (Region != INDEX_NONE)
                Points[Region].Add(Frames[Ref.FindBoneIndex(Names[Region])].InverseTransformPosition(FVector(Vertex.Position)));
        }
    const FString Path = FPackageName::GetLongPackagePath(InMesh->GetOutermost()->GetName()) / TEXT("PA_HundredEyedSlag_V2");
    UPackage* Package = CreatePackage(*Path);
    UPhysicsAsset* Asset = FindObject<UPhysicsAsset>(Package, TEXT("PA_HundredEyedSlag_V2"));
    if (!Asset) Asset = NewObject<UPhysicsAsset>(Package, TEXT("PA_HundredEyedSlag_V2"), RF_Public | RF_Standalone | RF_Transactional);
    Asset->Modify(); Asset->SkeletalBodySetups.Reset(); Asset->ConstraintSetup.Reset(); Asset->CollisionDisableTable.Reset();
    TArray<FBox> WorldBounds;
    for (int32 I = 0; I < UE_ARRAY_COUNT(Names); ++I)
    {
        if (Points[I].Num() < 8) return nullptr;
        FVector Min, Max;
        for (int32 Axis = 0; Axis < 3; ++Axis)
        {
            TArray<double> Coordinates; Coordinates.Reserve(Points[I].Num());
            for (const FVector& Point : Points[I]) Coordinates.Add(Point[Axis]);
            Coordinates.Sort();
            Min[Axis] = Coordinates[FMath::FloorToInt((Coordinates.Num()-1)*.005)];
            Max[Axis] = Coordinates[FMath::CeilToInt((Coordinates.Num()-1)*.995)];
        }
        const int32 Bone = Ref.FindBoneIndex(Names[I]);
        const float Scale = Frames[Bone].GetScale3D().GetAbsMax();
        auto* Setup = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
        Setup->BoneName = Names[I]; Setup->PhysicsType = PhysType_Default;
        Setup->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        // Palm boxes include attached fingers; no independent tiny finger bodies.
        FKBoxElem Shape; Shape.Center = (Min+Max)*.5;
        const FVector Size = (Max-Min).ComponentMax(FVector(3.f/Scale));
        Shape.X = Size.X; Shape.Y = Size.Y; Shape.Z = Size.Z;
        Setup->AggGeom.BoxElems.Add(Shape);
        Setup->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Setup->DefaultInstance.LinearDamping = .65f;
        Setup->DefaultInstance.AngularDamping = 1.8f;
        Setup->DefaultInstance.SetMassOverride(Masses[I]);
        Setup->DefaultInstance.bUseCCD = true;
        Setup->DefaultInstance.PositionSolverIterationCount = 16;
        Setup->DefaultInstance.VelocitySolverIterationCount = 8;
        Setup->InvalidatePhysicsData(); Setup->CreatePhysicsMeshes(); Asset->SkeletalBodySetups.Add(Setup);
        WorldBounds.Add(FBox(Min,Max).TransformBy(Frames[Bone]));
    }
    // A scaled imported container must participate in physics blending. Keeping
    // only a pelvis body makes UE inverse-scale through the animated container
    // a second time. This helper has no world contact and no skinned vertices.
    const FName ContainerBone = Ref.GetBoneName(0);
    auto* Container = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
    Container->BoneName = ContainerBone; Container->PhysicsType = PhysType_Default;
    Container->CollisionTraceFlag = CTF_UseSimpleAsComplex;
    FKSphereElem ContainerShape;
    ContainerShape.Radius = 2.f / FMath::Max(Frames[0].GetScale3D().GetAbsMax(), .001f);
    Container->AggGeom.SphereElems.Add(ContainerShape);
    Container->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
    Container->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Container->DefaultInstance.SetMassOverride(2.f);
    Container->DefaultInstance.LinearDamping = .65f;
    Container->DefaultInstance.AngularDamping = 1.8f;
    Container->InvalidatePhysicsData(); Container->CreatePhysicsMeshes();
    Asset->SkeletalBodySetups.Add(Container);
    Asset->UpdateBodySetupIndexMap();
    for (int32 I = 0; I < UE_ARRAY_COUNT(Names); ++I)
    {
        const int32 Bone = Ref.FindBoneIndex(Names[I]); int32 Parent = Ref.GetParentIndex(Bone);
        while (Parent >= 0 && Asset->FindBodyIndex(Ref.GetBoneName(Parent)) == INDEX_NONE) Parent = Ref.GetParentIndex(Parent);
        if (Parent < 0) continue;
        auto* Joint = NewObject<UPhysicsConstraintTemplate>(Asset, NAME_None, RF_Transactional);
        auto& C = Joint->DefaultInstance;
        C.JointName = Names[I]; C.ConstraintBone1 = Names[I]; C.ConstraintBone2 = Ref.GetBoneName(Parent);
        const FTransform Anchor(Frames[Bone].GetRotation(), Frames[Bone].GetLocation());
        C.SetRefFrame(EConstraintFrame::Frame1, Anchor.GetRelativeTransform(Frames[Bone]));
        C.SetRefFrame(EConstraintFrame::Frame2, Anchor.GetRelativeTransform(Frames[Parent]));
        C.SetLinearXLimit(LCM_Locked,0); C.SetLinearYLimit(LCM_Locked,0); C.SetLinearZLimit(LCM_Locked,0);
        const FString N = Names[I].ToString();
        const bool ContainerJoint = C.ConstraintBone2 == ContainerBone;
        const FVector Limits = N.Contains(TEXT("upper")) ? FVector(65,50,35)
            : N.Contains(TEXT("lower")) ? FVector(55,18,15)
            : N.Contains(TEXT("palm")) ? FVector(30,25,20) : FVector(18,18,12);
        C.SetAngularSwing1Limit(ContainerJoint ? ACM_Locked : ACM_Limited,Limits.X);
        C.SetAngularSwing2Limit(ContainerJoint ? ACM_Locked : ACM_Limited,Limits.Y);
        C.SetAngularTwistLimit(ContainerJoint ? ACM_Locked : ACM_Limited,Limits.Z); C.SetDisableCollision(true);
        // Serialize saves DefaultProfile, not the temporary editor instance.
        Joint->SetDefaultProfile(C);
        Asset->ConstraintSetup.Add(Joint); Asset->DisableCollision(I,Asset->FindBodyIndex(C.ConstraintBone2));
    }
    // Prevent interpenetrating reference hit volumes from explosively separating at handoff.
    for (int32 I = 0; I < WorldBounds.Num(); ++I)
        for (int32 J = I+1; J < WorldBounds.Num(); ++J)
            if (WorldBounds[I].Intersect(WorldBounds[J])) Asset->DisableCollision(I,J);
    Asset->UpdateBoundsBodiesArray(); Asset->MarkPackageDirty();
    InMesh->SetPhysicsAsset(Asset); InMesh->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("SLAG_FITTED_PHYSICS bodies=%d joints=%d mass_kg=103.5"),Asset->SkeletalBodySetups.Num(),Asset->ConstraintSetup.Num());
    return Asset;
#else
    return nullptr;
#endif
}

UPhysicsAsset* AHundredEyedSlagMonster::RepairCorpsePhysicsAsset(USkeletalMesh* InMesh, UPhysicsAsset* InPhysics)
{
#if WITH_EDITOR
    if (!InMesh || !InPhysics || InMesh->GetRefSkeleton().GetNum() == 0) return nullptr;
    const auto& Ref = InMesh->GetRefSkeleton();
    const FName ContainerBone = Ref.GetBoneName(0);
    const int32 PelvisBone = Ref.FindBoneIndex(TEXT("pelvis"));
    if (PelvisBone == INDEX_NONE) return nullptr;
    InPhysics->Modify();
    int32 ContainerIndex = InPhysics->FindBodyIndex(ContainerBone);
    // V16 authored a body for an assumed name that is absent from this skeleton.
    if (ContainerIndex == INDEX_NONE) ContainerIndex = InPhysics->FindBodyIndex(TEXT("Armature"));
    USkeletalBodySetup* Container = ContainerIndex != INDEX_NONE ? InPhysics->SkeletalBodySetups[ContainerIndex].Get() : nullptr;
    if (!Container)
    {
        Container = NewObject<USkeletalBodySetup>(InPhysics, NAME_None, RF_Transactional);
        InPhysics->SkeletalBodySetups.Add(Container);
    }
    Container->Modify(); Container->BoneName = ContainerBone; Container->PhysicsType = PhysType_Default;
    Container->CollisionTraceFlag = CTF_UseSimpleAsComplex;
    Container->AggGeom.EmptyElements();
    FKSphereElem Shape;
    Shape.Radius = 2.f / FMath::Max(Ref.GetRefBonePose()[0].GetScale3D().GetAbsMax(), .001f);
    Container->AggGeom.SphereElems.Add(Shape);
    Container->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
    Container->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Container->DefaultInstance.SetMassOverride(2.f);
    Container->DefaultInstance.LinearDamping = .65f; Container->DefaultInstance.AngularDamping = 1.8f;
    Container->InvalidatePhysicsData(); Container->CreatePhysicsMeshes();
    InPhysics->UpdateBodySetupIndexMap();
    TArray<FTransform> Frames = Ref.GetRefBonePose();
    for (int32 I = 0; I < Frames.Num(); ++I)
        if (Ref.GetParentIndex(I) >= 0) Frames[I] = Frames[I] * Frames[Ref.GetParentIndex(I)];
    for (const auto& JointPointer : InPhysics->ConstraintSetup)
    {
        auto* Joint = JointPointer.Get();
        if (!Joint) continue;
        Joint->Modify();
        auto& C = Joint->DefaultInstance;
        if (C.ConstraintBone2 == TEXT("Armature")) C.ConstraintBone2 = ContainerBone;
        const bool ContainerJoint = C.ConstraintBone2 == ContainerBone;
        C.SetLinearXLimit(LCM_Locked, 0.f); C.SetLinearYLimit(LCM_Locked, 0.f); C.SetLinearZLimit(LCM_Locked, 0.f);
        const FString Name = C.ConstraintBone1.ToString();
        const FVector Limits = Name.Contains(TEXT("upper")) ? FVector(65, 50, 35)
            : Name.Contains(TEXT("lower")) ? FVector(55, 18, 15)
            : Name.Contains(TEXT("palm")) ? FVector(30, 25, 20) : FVector(18, 18, 12);
        C.SetAngularSwing1Limit(ContainerJoint ? ACM_Locked : ACM_Limited, Limits.X);
        C.SetAngularSwing2Limit(ContainerJoint ? ACM_Locked : ACM_Limited, Limits.Y);
        C.SetAngularTwistLimit(ContainerJoint ? ACM_Locked : ACM_Limited, Limits.Z);
        C.SetDisableCollision(true);
        if (ContainerJoint)
        {
            const FTransform Anchor(Frames[PelvisBone].GetRotation(), Frames[PelvisBone].GetLocation());
            C.SetRefFrame(EConstraintFrame::Frame1, Anchor.GetRelativeTransform(Frames[PelvisBone]));
            C.SetRefFrame(EConstraintFrame::Frame2, Anchor.GetRelativeTransform(Frames[0]));
        }
        // The old setters updated DefaultInstance only. UPhysicsConstraintTemplate
        // replaces it with DefaultProfile during save, losing all authored limits.
        Joint->SetDefaultProfile(C);
        InPhysics->DisableCollision(InPhysics->FindBodyIndex(C.ConstraintBone1), InPhysics->FindBodyIndex(C.ConstraintBone2));
    }
    InPhysics->UpdateBoundsBodiesArray(); InPhysics->MarkPackageDirty();
    UE_LOG(LogTemp, Display, TEXT("SLAG_CORPSE_PHYSICS_AUTHORED root=%s bodies=%d joints=%d"),
        *ContainerBone.ToString(), InPhysics->SkeletalBodySetups.Num(), InPhysics->ConstraintSetup.Num());
    return InPhysics;
#else
    return nullptr;
#endif
}
