#include "HeQueMonster.h"
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

namespace HeQueHitSurface
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


bool AHeQueMonster::IsWeakpointHit(const FHitResult& Hit) const
{
    // The delivered rig weights the suspended heart to HQ_CoreSwing.
    // Bone_000 is only its inherited marker; the legs, arch and chain are body hits.
    return Hit.GetActor()==this&&Hit.GetComponent()==GetMesh()&&
        Hit.BoneName==TEXT("HQ_CoreSwing");
}

void AHeQueMonster::ResolveRemoteHit(const FVector& Origin,const FVector& Point,FHitResult& Hit) const
{
    // Remote reports still use the common range/cover checks. A claimed bone
    // alone cannot turn a leg hit into a heart hit; query the authority rig.
    Hit.BoneName=NAME_None;Hit.Component=GetMesh();
    const FVector Direction=(Point-Origin).GetSafeNormal();
    if(Direction.IsNearlyZero())return;
    FHitResult Contact;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueRemoteWeakpoint),true);
    if(GetMesh()->LineTraceComponent(Contact,Origin,Point+Direction*30.f,Query)
        &&FVector::DistSquared(Contact.ImpactPoint,Point)<=FMath::Square(60.f))Hit=Contact;
    // An out-of-date pose keeps the already-validated body hit, without granting
    // an unverified weakpoint. This is current-pose validation, not rewind.
}

UPhysicsAsset* AHeQueMonster::BuildHitSurfacePhysics(USkeletalMesh* InMesh,const FString& AssetPath)
{
#if WITH_EDITOR
    if(!InMesh||!AssetPath.StartsWith(TEXT("/Game/Monsters/HeQue/RigV01/"))||
       !InMesh->GetImportedModel()||InMesh->GetImportedModel()->LODModels.IsEmpty())return nullptr;
    const auto& Ref=InMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    TArray<FVector> Directions;
    for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)for(int32 Z=-1;Z<=1;++Z)
        if(X||Y||Z)Directions.Add(FVector(X,Y,Z).GetSafeNormal());
    TArray<HeQueHitSurface::FRegion> Regions;Regions.SetNum(Ref.GetNum());
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
