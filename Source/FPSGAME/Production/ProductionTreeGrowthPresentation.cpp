#include "ProductionHarvestSubsystem.h"
#include "ProductionObservers.h"
#include "Camera/PlayerCameraManager.h"
#include "ProductionHarvestAssets.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Animation/TransformProviderData.h"
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
    constexpr double CollisionRadius=9600.;
    TArray<FVector> LocalViews{Eye};
    for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if (const auto* PC=It->Get();PC && PC->IsLocalController() && PC->PlayerCameraManager)
            { const FVector View=PC->PlayerCameraManager->GetCameraLocation(); if(ProductionObservers::Distance(LocalViews,View)>FMath::Square(100.)) LocalViews.Add(View); }
    const auto Observers=ProductionObservers::Gather(GetWorld(),Eye);
    TMap<uint64,FTransform> CollisionWanted;
    TSet<uint64> Seen;
    auto Gather=[&](const FVector& View,double Range,bool Visual)
    {
        const FVector Extent(Range,Range,50000);
        const FBox Bounds(View-Extent,View+Extent);
        TArray<FTemperatePlacement> Near;
        Hills->GetRegrowingTrees(Bounds,Near);
        if(Hills->IsForestVillage()) Hills->GetForestStandingTrees(Bounds,Near);
        for(const auto& P:Near)
        {
            const double Dist=FVector::DistSquared2D(View,P.Transform.GetLocation());
            if (Dist>Range*Range) continue;
            if (Visual && !Seen.Contains(P.CandidateId)) {Seen.Add(P.CandidateId);Wanted.Add(P);}
            if (Dist<=CollisionRadius*CollisionRadius && P.Transform.GetScale3D().X>=.12)
                CollisionWanted.Add(P.CandidateId,P.Transform);
        }
    };
    for (const FVector& View:LocalViews) Gather(View,Radius,true);
    for (const FVector& View:Observers)
        if (!LocalViews.Contains(View)) Gather(View,CollisionRadius,false);
    Wanted.Sort([&](const auto& A,const auto& B){return ProductionObservers::Distance(LocalViews,A.Transform.GetLocation())<ProductionObservers::Distance(LocalViews,B.Transform.GetLocation());});
    for(auto It=State.Instances.CreateIterator();It;++It)
        if(!Seen.Contains(It.Key())){GrowthMeshes[It.Value().Variant]->RemoveInstance(It.Value().Id);It.RemoveCurrent();}
    if(Wanted.IsEmpty() && CollisionWanted.IsEmpty())
    {if(GrowthTrunks && !State.CollisionIds.IsEmpty())GrowthTrunks->ClearInstances();State.CollisionIds.Empty();return;}
    if(!Wanted.IsEmpty() && GrowthMeshes.IsEmpty())
    {
        for(const auto& Tree:Hills->Assets->Trees)if(!Tree.IsValid())return;
        for(const auto& Tree:Hills->Assets->Trees)
        {
            auto* Mesh=NewObject<UInstancedSkinnedMeshComponent>(Hills.Get());
            Mesh->ComponentTags.Add(TEXT("HarvestRegrowth"));
            Hills->AddInstanceComponent(Mesh);Mesh->SetupAttachment(Hills->GetRootComponent());
            Mesh->SetSkinnedAsset(Tree.Get());Mesh->SetMobility(EComponentMobility::Movable);
            if(Hills->Assets->ForestWindProvider)Mesh->SetTransformProvider(Hills->Assets->ForestWindProvider);
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);
            Mesh->RegisterComponent();GrowthMeshes.Add(Mesh);
        }
    }
    // Only transformed instances are updated. Ordinary PCG trees are never regenerated.
    const int32 AddBudget=Hills->IsForestVillage()?48:8;
    int32 Added=0;
    for(const auto& P:Wanted)
    {
        if(auto* Entry=State.Instances.Find(P.CandidateId))
        {
            if(!Entry->Transform.Equals(P.Transform,.00001))
            {GrowthMeshes[Entry->Variant]->UpdateInstance(Entry->Id,P.Transform,0,true);Entry->Transform=P.Transform;}
            continue;
        }
        if(Added>=AddBudget)continue;
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
    for(const auto& Pair:CollisionWanted)
    {
        const auto& T=Pair.Value;const double Scale=T.GetScale3D().X;
        const FTransform Collision(T.GetRotation(),T.GetLocation()+FVector(0,0,300*Scale),FVector(.42*Scale,.42*Scale,6*Scale));
        if(auto* Entry=State.CollisionIds.Find(Pair.Key))
        {
            if(!Entry->Transform.Equals(Collision,.00001))
            {GrowthTrunks->UpdateInstanceTransformById(Entry->Id,Collision,true,true);Entry->Transform=Collision;}
        }
        else State.CollisionIds.Add(Pair.Key,{GrowthTrunks->AddInstanceById(Collision,true),Collision});
    }
    for(auto It=State.CollisionIds.CreateIterator();It;++It)
        if(!CollisionWanted.Contains(It.Key())){GrowthTrunks->RemoveInstanceById(It.Value().Id);It.RemoveCurrent();}
}
