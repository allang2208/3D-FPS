#include "ProductionHarvestSubsystem.h"
#include "ProductionHarvestAssets.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

struct FProductionTreeGrowthPresentation
{
    struct FInstance { int32 Variant; FPrimitiveInstanceId Id; FTransform Transform; };
    struct FCollision { FPrimitiveInstanceId Id; FTransform Transform; };
    TMap<uint64,FInstance> Instances;
    TMap<uint64,FCollision> CollisionIds;
    double NextUpdate=0;
};

void UProductionHarvestSubsystem::RemoveGrowingTree(uint64 Candidate)
{
    if(!GrowingTrees)return;
    if(const auto* Entry=GrowingTrees->Instances.Find(Candidate))
        if(GrowthMeshes.IsValidIndex(Entry->Variant))GrowthMeshes[Entry->Variant]->RemoveInstance(Entry->Id);
    GrowingTrees->Instances.Remove(Candidate);
    // CompleteProductionHarvest already removed the hit collision instance.
    GrowingTrees->CollisionIds.Remove(Candidate);
    GrowingTrees->NextUpdate=0;
}

void UProductionHarvestSubsystem::ClearGrowingTrees()
{
    for(auto& Mesh:GrowthMeshes)if(Mesh)Mesh->DestroyComponent();GrowthMeshes.Empty();
    if(GrowthTrunks)GrowthTrunks->DestroyComponent();GrowthTrunks=nullptr;
    GrowingTrees.Reset();
}

void UProductionHarvestSubsystem::UpdateGrowingTrees(const FVector& Eye,double Now)
{
    if(!Hills.IsValid()||!Hills->Assets)return;
    if(!GrowingTrees)GrowingTrees=MakeShared<FProductionTreeGrowthPresentation>();
    auto& State=*GrowingTrees;
    if(Now<State.NextUpdate)return;State.NextUpdate=Now+1;
    TArray<FTemperatePlacement> Wanted;
    constexpr double Radius=25600; // bounded local presentation for recurrent trees
    Hills->GetRegrowingTrees(FBox(Eye-FVector(Radius,Radius,50000),Eye+FVector(Radius,Radius,50000)),Wanted);
    Wanted.RemoveAll([&](const auto& P){return FVector::DistSquared2D(P.Transform.GetLocation(),Eye)>Radius*Radius;});
    Wanted.Sort([&](const auto& A,const auto& B){return FVector::DistSquared2D(A.Transform.GetLocation(),Eye)<FVector::DistSquared2D(B.Transform.GetLocation(),Eye);});
    TSet<uint64> Keys;for(const auto& P:Wanted)Keys.Add(P.CandidateId);
    for(auto It=State.Instances.CreateIterator();It;++It)
        if(!Keys.Contains(It.Key())){GrowthMeshes[It.Value().Variant]->RemoveInstance(It.Value().Id);It.RemoveCurrent();}
    if(Wanted.IsEmpty()&&State.Instances.IsEmpty())
    {if(GrowthTrunks)GrowthTrunks->ClearInstances();State.CollisionIds.Empty();return;}
    if(GrowthMeshes.IsEmpty())
    {
        for(const auto& Tree:Hills->Assets->Trees)if(!Tree.IsValid())return;
        for(const auto& Tree:Hills->Assets->Trees)
        {
            auto* Mesh=NewObject<UInstancedSkinnedMeshComponent>(Hills.Get());
            Hills->AddInstanceComponent(Mesh);Mesh->SetupAttachment(Hills->GetRootComponent());
            Mesh->SetSkinnedAsset(Tree.Get());Mesh->SetMobility(EComponentMobility::Movable);
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);
            Mesh->RegisterComponent();GrowthMeshes.Add(Mesh);
        }
    }
    // Only transformed instances are updated. Ordinary PCG trees are never regenerated.
    int32 Added=0;
    for(const auto& P:Wanted)
    {
        if(auto* Entry=State.Instances.Find(P.CandidateId))
        {
            if(!Entry->Transform.Equals(P.Transform,.00001))
            {GrowthMeshes[Entry->Variant]->UpdateInstance(Entry->Id,P.Transform,0,true);Entry->Transform=P.Transform;}
            continue;
        }
        if(Added>=8)continue;
        const int32 Variant=Hills->Assets->Trees.IndexOfByPredicate([&](const auto& T){return T.ToSoftObjectPath()==P.Mesh;});
        if(!GrowthMeshes.IsValidIndex(Variant))continue;
        const auto Id=GrowthMeshes[Variant]->AddInstance(P.Transform,0,true);
        State.Instances.Add(P.CandidateId,{Variant,Id,P.Transform});++Added;
    }
    if(!GrowthTrunks && Hills->Assets->TrunkCollisionMesh.IsValid())
    {
        GrowthTrunks=NewObject<UInstancedStaticMeshComponent>(Hills.Get());Hills->AddInstanceComponent(GrowthTrunks);
        GrowthTrunks->SetupAttachment(Hills->GetRootComponent());GrowthTrunks->SetMobility(EComponentMobility::Movable);
        GrowthTrunks->SetStaticMesh(Hills->Assets->TrunkCollisionMesh.Get());GrowthTrunks->SetCollisionProfileName(TEXT("BlockAll"));
        GrowthTrunks->SetVisibility(false);GrowthTrunks->SetCastShadow(false);GrowthTrunks->SetCanEverAffectNavigation(false);
        GrowthTrunks->RegisterComponent();
    }
    if(!GrowthTrunks)return;
    TSet<uint64> CollisionKeys;
    for(const auto& Pair:State.Instances)
    {
        const auto& T=Pair.Value.Transform;const double Scale=T.GetScale3D().X;
        if(Scale<.12 || FVector::DistSquared2D(T.GetLocation(),Eye)>FMath::Square(9600.0))continue;
        CollisionKeys.Add(Pair.Key);
        const FTransform Collision(T.GetRotation(),T.GetLocation()+FVector(0,0,300*Scale),FVector(.42*Scale,.42*Scale,6*Scale));
        if(auto* Entry=State.CollisionIds.Find(Pair.Key))
        {
            if(!Entry->Transform.Equals(Collision,.00001))
            {GrowthTrunks->UpdateInstanceTransformById(Entry->Id,Collision,true,true);Entry->Transform=Collision;}
        }
        else State.CollisionIds.Add(Pair.Key,{GrowthTrunks->AddInstanceById(Collision,true),Collision});
    }
    for(auto It=State.CollisionIds.CreateIterator();It;++It)
        if(!CollisionKeys.Contains(It.Key())){GrowthTrunks->RemoveInstanceById(It.Value().Id);It.RemoveCurrent();}
}
