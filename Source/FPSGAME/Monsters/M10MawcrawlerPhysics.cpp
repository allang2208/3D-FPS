#include "M10Mawcrawler.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

bool AM10Mawcrawler::BuildPhysics(USkeletalMesh* SourceMesh,UPhysicsAsset* Asset)
{
#if WITH_EDITOR
    if(!SourceMesh||!Asset||!SourceMesh->GetImportedModel()||SourceMesh->GetImportedModel()->LODModels.IsEmpty())return false;
    const auto& Ref=SourceMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    TArray<FName> Names={TEXT("root"),TEXT("body_center"),TEXT("body_front"),TEXT("body_rear"),TEXT("rump"),TEXT("head"),TEXT("jaw")};
    for(const TCHAR* Side:{TEXT("L"),TEXT("R")})for(int32 Pair=1;Pair<=4;++Pair)
        for(const TCHAR* Part:{TEXT("upper"),TEXT("lower"),TEXT("foot")})Names.Add(FName(*FString::Printf(TEXT("leg_%02d_%s_%s"),Pair,Side,Part)));
    TArray<TArray<FVector>> Points;Points.SetNum(Names.Num());
    for(const auto& Section:SourceMesh->GetImportedModel()->LODModels[0].Sections)for(const auto& Vertex:Section.SoftVertices)
    {
        int32 Dominant=0;
        for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(Vertex.InfluenceWeights[J]>Vertex.InfluenceWeights[Dominant])Dominant=J;
        int32 Bone=Section.BoneMap[Vertex.InfluenceBones[Dominant]];int32 Region=INDEX_NONE;
        while(Bone>=0)
        {
            Region=Names.IndexOfByKey(Ref.GetBoneName(Bone));if(Region!=INDEX_NONE)break;Bone=Ref.GetParentIndex(Bone);
        }
        if(Region>0)Points[Region].Add(Frames[Bone].InverseTransformPosition(FVector(Vertex.Position)));
    }
    Asset->Modify();Asset->SkeletalBodySetups.Reset();Asset->ConstraintSetup.Reset();Asset->CollisionDisableTable.Reset();
    TArray<FBox> Bounds;
    for(int32 I=0;I<Names.Num();++I)
    {
        const int32 Bone=Ref.FindBoneIndex(Names[I]);if(Bone==INDEX_NONE)return false;
        auto* Body=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);Body->BoneName=Names[I];
        Body->PhysicsType=PhysType_Default;Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        if(I==0)
        {
            FKSphereElem Sphere;Sphere.Radius=1.f/Frames[Bone].GetScale3D().GetAbsMax();Body->AggGeom.SphereElems.Add(Sphere);
        }
        else
        {
            if(Points[I].Num()<4)return false;
            // Convex support points fit each weighted region's real surface.
            // A fixed direction budget keeps hull cooking independent of source density.
            FKConvexElem Hull;
            for(int32 X=-2;X<=2;++X)for(int32 Y=-2;Y<=2;++Y)for(int32 Z=-2;Z<=2;++Z)
            {
                if(X==0&&Y==0&&Z==0)continue;
                const FVector Direction(X,Y,Z);float Best=-FLT_MAX;FVector Point=FVector::ZeroVector;
                for(const FVector& P:Points[I]){const float Dot=FVector::DotProduct(P,Direction);if(Dot>Best){Best=Dot;Point=P;}}
                Hull.VertexData.AddUnique(Point);
            }
            Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(Hull);
        }
        const FString Name=Names[I].ToString();
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
        Body->DefaultInstance.SetMassOverride(I==0?.1f:I==1?100.f:I<5?60.f:I==5?35.f:I==6?12.f:Name.EndsWith(TEXT("foot"))?4.f:8.f);
        Body->DefaultInstance.LinearDamping=.25f;Body->DefaultInstance.AngularDamping=.9f;
        Body->DefaultInstance.bUseCCD=true;Body->DefaultInstance.PositionSolverIterationCount=12;Body->DefaultInstance.VelocitySolverIterationCount=4;
        if(I==0)Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();Bounds.Add(Body->AggGeom.CalcAABB(Frames[Bone]));
        Asset->SkeletalBodySetups.Add(Body);
    }
    Asset->UpdateBodySetupIndexMap();
    for(int32 I=1;I<Names.Num();++I)
    {
        const int32 Bone=Ref.FindBoneIndex(Names[I]);int32 Parent=Ref.GetParentIndex(Bone);
        while(Parent>=0&&!Names.Contains(Ref.GetBoneName(Parent)))Parent=Ref.GetParentIndex(Parent);
        if(Parent<0)return false;
        auto* Joint=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);auto& C=Joint->DefaultInstance;
        C.JointName=Names[I];C.ConstraintBone1=Names[I];C.ConstraintBone2=Ref.GetBoneName(Parent);
        const FTransform Anchor(Frames[Bone].GetRotation(),Frames[Bone].GetLocation());
        C.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(Frames[Bone]));
        C.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(Frames[Parent]));
        C.SetLinearXLimit(LCM_Locked,0.f);C.SetLinearYLimit(LCM_Locked,0.f);C.SetLinearZLimit(LCM_Locked,0.f);
        const FString Name=Names[I].ToString();const bool Limb=Name.StartsWith(TEXT("leg_"));
        const bool Hinge=Name.EndsWith(TEXT("lower"))||Name==TEXT("jaw");
        C.SetAngularSwing1Limit(ACM_Limited,Hinge?50.f:Limb?40.f:15.f);
        C.SetAngularSwing2Limit(ACM_Limited,Hinge?10.f:Limb?25.f:12.f);
        C.SetAngularTwistLimit(ACM_Limited,Hinge?8.f:Limb?20.f:10.f);
        C.SetDisableCollision(true);C.DisableProjection();C.SetShockPropagationParams(false,0.f);
        C.SetOrientationDriveTwistAndSwing(false,false);C.SetAngularVelocityDriveTwistAndSwing(false,false);
        Joint->SetDefaultProfile(C);Asset->ConstraintSetup.Add(Joint);
        Asset->DisableCollision(I,Asset->FindBodyIndex(C.ConstraintBone2));
    }
    for(int32 I=0;I<Names.Num();++I)for(int32 J=I+1;J<Names.Num();++J)
        if(I==0||Bounds[I].Intersect(Bounds[J]))Asset->DisableCollision(I,J);
    Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();SourceMesh->SetPhysicsAsset(Asset);SourceMesh->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
