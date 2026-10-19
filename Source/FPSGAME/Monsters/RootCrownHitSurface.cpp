#include "RootCrownRigPreview.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "UObject/Package.h"

namespace RootCrownHitSurface
{
struct FRegion
{
    int32 Count=0;FVector Points[26];double Support[26];
    FRegion(){for(double& V:Support)V=-DBL_MAX;}
    void Add(const FVector& P,const TArray<FVector>& Directions)
    {
        ++Count;
        for(int32 I=0;I<Directions.Num();++I)
            if(const double D=FVector::DotProduct(P,Directions[I]);D>Support[I]){Support[I]=D;Points[I]=P;}
    }
};
}
#endif

bool ARootCrownRigPreview::IsWeakpointHit(const FHitResult& Hit) const
{
    // The ten fan leaves are ordinary tissue; the connecting stem is the weakpoint.
    return Hit.GetActor()==this&&(!Hit.GetComponent()||Hit.GetComponent()==GetMesh())&&
        (Hit.BoneName==TEXT("Stem_Lower")||Hit.BoneName==TEXT("Stem_Upper")||Hit.BoneName==TEXT("Crown_Base"));
}
UPhysicsAsset* ARootCrownRigPreview::BuildHitSurfacePhysics(USkeletalMesh* InMesh,const FString& AssetPath)
{
#if WITH_EDITOR
    if(!InMesh||!AssetPath.StartsWith(TEXT("/Game/Monsters/RootCrown/CombatV01/"))||
       !InMesh->GetImportedModel()||InMesh->GetImportedModel()->LODModels.IsEmpty())return nullptr;
    const auto& Ref=InMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    TArray<FVector> Directions;
    for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)for(int32 Z=-1;Z<=1;++Z)
        if(X||Y||Z)Directions.Add(FVector(X,Y,Z).GetSafeNormal());
    TArray<RootCrownHitSurface::FRegion> Regions;Regions.SetNum(Ref.GetNum());
    for(const auto& Section:InMesh->GetImportedModel()->LODModels[0].Sections)for(const auto& V:Section.SoftVertices)
    {
        uint32 Total=0;int32 Dominant=0;
        for(int32 J=0;J<MAX_TOTAL_INFLUENCES;++J)
        {Total+=V.InfluenceWeights[J];if(V.InfluenceWeights[J]>V.InfluenceWeights[Dominant])Dominant=J;}
        for(int32 J=0;J<MAX_TOTAL_INFLUENCES;++J)
        {
            // Overlap shared skin boundaries, without bridging separate crown leaves or legs.
            if(!V.InfluenceWeights[J]||(J!=Dominant&&uint32(V.InfluenceWeights[J])*4<Total))continue;
            const int32 Bone=Section.BoneMap[V.InfluenceBones[J]];
            Regions[Bone].Add(Frames[Bone].InverseTransformPosition(FVector(V.Position)),Directions);
        }
    }
    UPackage* Package=CreatePackage(*AssetPath);const FName Name(*FPackageName::GetLongPackageAssetName(AssetPath));
    auto* Asset=FindObject<UPhysicsAsset>(Package,*Name.ToString());const bool NewAsset=!Asset;
    if(!Asset)Asset=NewObject<UPhysicsAsset>(Package,Name,RF_Public|RF_Standalone|RF_Transactional);
    Asset->Modify();Asset->SkeletalBodySetups.Reset();Asset->ConstraintSetup.Reset();Asset->CollisionDisableTable.Reset();
    for(int32 Bone=0;Bone<Ref.GetNum();++Bone)
    {
        const auto& Region=Regions[Bone];if(Region.Count<4)continue;
        FKConvexElem Hull;const double Padding=.6/FMath::Max(.001,Frames[Bone].GetScale3D().GetAbsMax());
        for(int32 D=0;D<Directions.Num();++D)Hull.VertexData.AddUnique(Region.Points[D]+Directions[D]*Padding);
        if(Hull.VertexData.Num()<4)continue;
        Hull.UpdateElemBox();auto* Body=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);
        Body->BoneName=Ref.GetBoneName(Bone);Body->PhysicsType=PhysType_Kinematic;Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryOnly);
        Body->AggGeom.ConvexElems.Add(MoveTemp(Hull));Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();
        Asset->SkeletalBodySetups.Add(Body);
    }
    Asset->UpdateBodySetupIndexMap();Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();
    if(NewAsset)FAssetRegistryModule::AssetCreated(Asset);
    return Asset;
#else
    return nullptr;
#endif
}
