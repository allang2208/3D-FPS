#include "TemperateHillsWorld.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionFallingTree.h"
#include "../Production/ProductionHarvestSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "PCGComponent.h"
#include "UObject/UObjectIterator.h"

FString ATemperateHillsWorld::ProductionResourceId(int32 Layer,uint64 Candidate) const
{
    return FString::Printf(TEXT("%s:v1:%d:%016llx"),*WorldId.ToString(EGuidFormats::Digits),Layer,Candidate);
}
bool ATemperateHillsWorld::IsProductionDepleted(int32 Layer,uint64 Candidate) const
{
    const auto* Profile=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    return Profile && Profile->HarvestProgress(ProductionResourceId(Layer,Candidate))>=FProductionResource::RequiredHits;
}

bool ATemperateHillsWorld::ResolveProductionResource(const FHitResult& Hit,FProductionResource& Resource,FString& Reason) const
{
    if (!bReady || !Assets || !WorldId.IsValid()) return false;
    const auto* Component=Hit.GetComponent();
    if (!Component) return false;
    if (const auto* TerrainMesh=Cast<UDynamicMeshComponent>(Component);TerrainMesh && Terrain.Contains(TerrainMesh))
    {
        const FVector P=Hit.ImpactPoint;
        if (Hit.ImpactNormal.Z<.65 || (RiverPlan && RiverPlan->Sample(P.X,P.Y).Wet>.05))
        { Reason=TEXT("陡坡或河床不可铲取表土"); return false; }
        const int32 X=FMath::FloorToInt(P.X/250),Y=FMath::FloorToInt(P.Y/250);
        Resource.CandidateId=(uint64(uint32(X))<<32)|uint32(Y);
        Resource.Layer=2; Resource.World=const_cast<ATemperateHillsWorld*>(this);
        Resource.Id=ProductionResourceId(2,Resource.CandidateId); Resource.Name=TEXT("表土");
        Resource.RequiredTool=TEXT("shovel"); Resource.Rewards.Add(TEXT("soil"),2);
        Resource.Transform=FTransform(FVector((X+.5)*250,(Y+.5)*250,Height((X+.5)*250,(Y+.5)*250)));
        return true;
    }
    const auto* MeshComponent=Cast<UStaticMeshComponent>(Component);
    if (!MeshComponent || !MeshComponent->GetStaticMesh()) return false;
    const bool Tree=MeshComponent->GetOwner()==this && MeshComponent->GetStaticMesh()==Assets->TrunkCollisionMesh.Get();
    const int32 Layer=Tree?0:1;
    FTransform Transform=MeshComponent->GetComponentTransform();
    if (const auto* ISM=Cast<UInstancedStaticMeshComponent>(Component))
        if (!ISM->GetInstanceTransform(Hit.Item,Transform,true)) return false;
    FVector Origin=Transform.GetLocation();
    if (Tree) Origin.Z-=300*Transform.GetScale3D().Z/6;
    TArray<FTemperatePlacement> Candidates;
    GetPlacements(Layer,FBox(Origin-FVector(50,50,50000),Origin+FVector(50,50,50000)),Candidates);
    for (const auto& Candidate:Candidates)
    {
        if (FVector2D::DistSquared(FVector2D(Origin),FVector2D(Candidate.Transform.GetLocation()))>25) continue;
        if (!Tree && Candidate.Mesh.ToString()!=MeshComponent->GetStaticMesh()->GetPathName()) continue;
        if (!Tree && MeshComponent->GetStaticMesh()->GetBounds().SphereRadius*Transform.GetScale3D().GetAbsMax()>500)
        { Reason=TEXT("大型岩壁不可采集，请寻找独立岩块"); return false; }
        Resource.World=const_cast<ATemperateHillsWorld*>(this); Resource.Layer=Layer;
        Resource.Transform=Candidate.Transform; Resource.Mesh=Candidate.Mesh; Resource.Seed=Candidate.Key;
        Resource.CandidateId=Candidate.CandidateId; Resource.Id=ProductionResourceId(Layer,Candidate.CandidateId);
        Resource.RequiredTool=Tree?TEXT("axe"):TEXT("pickaxe");
        if (Tree) { Resource.Name=TEXT("树木"); Resource.Rewards.Add(TEXT("wood"),4); }
        else
        {
            const uint32 Pick=Candidate.Key%100;
            const FString Ore=Pick<25?TEXT("iron_ore"):Pick<37?TEXT("copper_ore"):Pick<41?TEXT("silver_ore"):Pick<43?TEXT("gold_ore"):TEXT("");
            Resource.Name=Ore==TEXT("iron_ore")?TEXT("含铁岩块"):Ore==TEXT("copper_ore")?TEXT("含铜岩块"):
                Ore==TEXT("silver_ore")?TEXT("含银岩块"):Ore==TEXT("gold_ore")?TEXT("含金岩块"):TEXT("石块");
            Resource.Rewards.Add(TEXT("stone"),Ore.IsEmpty()?3:1);
            if (!Ore.IsEmpty()) Resource.Rewards.Add(Ore,2);
        }
        return true;
    }
    return false;
}

void ATemperateHillsWorld::CompleteProductionHarvest(const FProductionResource& Resource,const FHitResult& Hit,const FVector& Direction)
{
    if (Resource.Layer==2) return; // Soil is a finite surface harvest, not terrain excavation.
    if (auto* ISM=Cast<UInstancedStaticMeshComponent>(Hit.GetComponent())) ISM->RemoveInstance(Hit.Item);
    if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())
    {
        Harvest->Burst(Resource.Layer==0,Hit.ImpactPoint,Resource.Seed);
        if(Resource.Layer==0)Harvest->RefreshStumps();
    }
    if (Resource.Layer==0)
    {
        // Remove only the rendered tree instance. Stable candidate IDs remain in
        // the profile, so subsequent PCG streaming cannot restore the felled tree.
        for(TObjectIterator<UInstancedSkinnedMeshComponent> It;It;++It)
        {
            auto* Trees=*It;
            if(Trees->GetWorld()!=GetWorld()||Trees->GetSkinnedAsset()!=Resource.Mesh.ResolveObject())continue;
            for(int32 N=Trees->GetInstanceCount()-1;N>=0;--N)
            {
                const auto Id=Trees->GetInstanceId(N);FTransform Transform;
                if(Trees->GetInstanceTransform(Id,Transform,true)&&FVector::DistSquared(Transform.GetLocation(),Resource.Transform.GetLocation())<4)
                {Trees->RemoveInstance(Id);break;}
            }
        }
        FActorSpawnParameters Spawn; Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if (auto* Fall=GetWorld()->SpawnActor<AProductionFallingTree>(Resource.Transform.GetLocation(),Resource.Transform.Rotator(),Spawn)) Fall->InitializeFall(Resource,Direction);
    }
    // No PCG cell regeneration on each harvest; only the affected instances change.
}

void ATemperateHillsWorld::GetHarvestedStumps(const FBox& Bounds,TArray<FTransform>& Out) const
{
    // Reconstruct from the same seeded candidates and persisted depletion IDs.
    // No second stump save schema, and no tree/PCG regeneration on each chop.
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/1200);Y<=FMath::FloorToInt(Bounds.Max.Y/1200);++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/1200);X<=FMath::FloorToInt(Bounds.Max.X/1200);++X)
    {
        FTemperatePlacement P;
        if(TreeCandidate(X,Y,P)&&Bounds.IsInsideXY(P.Transform.GetLocation())&&IsProductionDepleted(0,P.CandidateId))
            Out.Add(P.Transform);
    }
}
