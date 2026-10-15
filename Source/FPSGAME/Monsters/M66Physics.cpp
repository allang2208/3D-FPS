#include "M66IncineratorMonster.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Misc/PackageName.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

UPhysicsAsset* AM66IncineratorMonster::BuildReactionPhysics(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
    if (!InMesh || !InMesh->GetImportedModel() || InMesh->GetImportedModel()->LODModels.IsEmpty()) return nullptr;
    const FName Names[] = {TEXT("Bone_001"),TEXT("Bone_006"),TEXT("Bone_004"),TEXT("Bone_020"),TEXT("M66_BackAnchor"),
        TEXT("Bone_027"),TEXT("Bone_026"),TEXT("Bone_037"),TEXT("Bone_032"),TEXT("Bone_031"),TEXT("Bone_029"),
        TEXT("Bone_012"),TEXT("Bone_011"),TEXT("Bone_010"),TEXT("Bone_017"),TEXT("Bone_016"),TEXT("Bone_015"),
        TEXT("M66_Vent_High_Base"),TEXT("M66_Vent_Rear_Base"),TEXT("M66_Vent_Front_Base"),TEXT("M66_Vent_Lateral_Base")};
    const float Masses[] = {55,40,35,35,60,30,25,18,10,6,4,25,18,8,25,18,8,4,4,4,3};
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
    for(FName Name:{FName(TEXT("Bone_000")),FName(TEXT("Bone_002")),FName(TEXT("Bone_003"))})
        if(const int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE)BoneToBody[I]=0;
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
    const FString Path = TEXT("/Game/Monsters/IncineratorBossM66/DeathGroundV07/PA_M66_Surface_V07");
    UPackage* Package = CreatePackage(*Path);
    UPhysicsAsset* Asset = FindObject<UPhysicsAsset>(Package, TEXT("PA_M66_Surface_V07"));
    if (!Asset) Asset = NewObject<UPhysicsAsset>(Package, TEXT("PA_M66_Surface_V07"), RF_Public | RF_Standalone | RF_Transactional);
    Asset->Modify(); Asset->SkeletalBodySetups.Reset(); Asset->ConstraintSetup.Reset(); Asset->CollisionDisableTable.Reset();
    for (int32 I = 0; I < UE_ARRAY_COUNT(Names); ++I)
    {
        if (Points[I].Num() < 8) {UE_LOG(LogTemp,Error,TEXT("M66_PHYSICS no fitted volume for %s (%d vertices)"),*Names[I].ToString(),Points[I].Num());return nullptr;}
        auto* Setup = NewObject<USkeletalBodySetup>(Asset, NAME_None, RF_Transactional);
        Setup->BoneName = Names[I]; Setup->PhysicsType = PhysType_Default;
        Setup->CollisionTraceFlag = CTF_UseSimpleAsComplex;
        // Rotated boxes extended 25-44 cm below the visible feet/death pose.
        // Select real surface support points for a bounded convex hull instead:
        // no empty box corners, and no extra bodies for individual fingers.
        FKConvexElem Shape;
        for (int32 DirectionIndex=0;DirectionIndex<134;++DirectionIndex)
        {
            FVector Direction;
            if(DirectionIndex<6)
            {
                Direction=FVector::ZeroVector;
                Direction[DirectionIndex/2]=DirectionIndex%2?1.:-1.;
            }
            else
            {
                const double Z=1.-2.*(DirectionIndex-6+.5)/128.;
                const double Angle=(DirectionIndex-6)*2.399963229728653;
                const double Radius=FMath::Sqrt(FMath::Max(0.,1.-Z*Z));
                Direction=FVector(Radius*FMath::Cos(Angle),Radius*FMath::Sin(Angle),Z);
            }
            double Best=-TNumericLimits<double>::Max();FVector Support=FVector::ZeroVector;
            for(const FVector& Point:Points[I])
                if(const double Distance=FVector::DotProduct(Point,Direction);Distance>Best)
                {Best=Distance;Support=Point;}
            Shape.VertexData.AddUnique(Support);
        }
        Shape.UpdateElemBox();Setup->AggGeom.ConvexElems.Add(MoveTemp(Shape));
        Setup->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Setup->DefaultInstance.LinearDamping = .65f;
        Setup->DefaultInstance.AngularDamping = 1.8f;
        Setup->DefaultInstance.SetMassOverride(Masses[I]);
        Setup->DefaultInstance.bUseCCD = true;
        Setup->DefaultInstance.PositionSolverIterationCount = 16;
        Setup->DefaultInstance.VelocitySolverIterationCount = 8;
        Setup->InvalidatePhysicsData(); Setup->CreatePhysicsMeshes(); Asset->SkeletalBodySetups.Add(Setup);
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
        const bool Knee=N==TEXT("Bone_011")||N==TEXT("Bone_016");
        const bool Arm=N==TEXT("Bone_027")||N==TEXT("Bone_032");
        const bool Hip=N==TEXT("Bone_012")||N==TEXT("Bone_017");
        const bool Elbow=N==TEXT("Bone_026")||N==TEXT("Bone_031");
        const FVector Limits=Knee?FVector(65,12,12):Arm?FVector(65,50,35):Hip?FVector(50,35,25)
            :Elbow?FVector(65,15,15):FVector(22,22,18);
        C.SetAngularSwing1Limit(ContainerJoint ? ACM_Locked : ACM_Limited,Limits.X);
        C.SetAngularSwing2Limit(ContainerJoint ? ACM_Locked : ACM_Limited,Limits.Y);
        C.SetAngularTwistLimit(ContainerJoint ? ACM_Locked : ACM_Limited,Limits.Z); C.SetDisableCollision(true);
        // Serialize saves DefaultProfile, not the temporary editor instance.
        Joint->SetDefaultProfile(C);
        Asset->ConstraintSetup.Add(Joint); Asset->DisableCollision(I,Asset->FindBodyIndex(C.ConstraintBone2));
    }
    // Overlapping sacs and oversized asymmetric limbs have no self contacts.
    // All bodies retain world collisions; joints limit relative articulation.
    for (int32 I=0;I<Asset->SkeletalBodySetups.Num();++I)
        for(int32 J=I+1;J<Asset->SkeletalBodySetups.Num();++J)Asset->DisableCollision(I,J);
    Asset->UpdateBoundsBodiesArray(); Asset->MarkPackageDirty();
    // The rare budget fallback grounds the visible surface once, rather than
    // the rotated broad-phase bounds of a collision shape.
    if(auto* LOD=InMesh->GetLODInfo(0);LOD&&!LOD->bAllowCPUAccess)
    {
        InMesh->Modify();LOD->bAllowCPUAccess=true;
        InMesh->PostEditChange();InMesh->MarkPackageDirty();
    }
    UE_LOG(LogTemp,Display,TEXT("M66_SURFACE_PHYSICS bodies=%d joints=%d convex=%d"),Asset->SkeletalBodySetups.Num(),Asset->ConstraintSetup.Num(),UE_ARRAY_COUNT(Names));
    return Asset;
#else
    return nullptr;
#endif
}
