#include "ProductionFallingTree.h"
#include "ProductionHarvestSubsystem.h"
#include "ProductionHarvestAssets.h"
#include "ProductionResource.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/SkinnedAsset.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"
#include "UObject/UObjectIterator.h"

void AProductionFallingTree::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AProductionFallingTree,NetFall);}

void AProductionFallingTree::OnRep_Fall()
{
    if(!NetFall.Valid||HasAuthority()||bFallReady)return;
    // Remove this standing instance immediately; the durable harvest snapshot
    // independently prevents streamed cells from reconstructing it later.
    for(TObjectIterator<UInstancedSkinnedMeshComponent> It;It;++It)
        if(It->GetWorld()==GetWorld()&&It->GetSkinnedAsset()&&It->GetSkinnedAsset()->GetPathName()==NetFall.Mesh.ToString())
            for(int32 N=It->GetInstanceCount()-1;N>=0;--N)
            {
                const auto Id=It->GetInstanceId(N);FTransform T;
                if(It->GetInstanceTransform(Id,T,true)&&FVector::DistSquared(T.GetLocation(),NetFall.Transform.GetLocation())<4.)It->RemoveInstance(Id);
            }
    for(TObjectIterator<UInstancedStaticMeshComponent> It;It;++It)
        if(It->GetWorld()==GetWorld()&&It->GetOwner()&&It->GetOwner()->IsA<ATemperateHillsWorld>()&&!It->ComponentHasTag(TEXT("HarvestStump")))
            for(int32 N=It->GetInstanceCount()-1;N>=0;--N)
            {
                FTransform T;
                if(It->GetInstanceTransform(N,T,true)&&FVector::DistSquared2D(T.GetLocation(),NetFall.Transform.GetLocation())<4.)It->RemoveInstance(N);
            }
    if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())
    {FProductionResource Resource;Resource.Mesh=NetFall.Mesh;Resource.Layer=0;Harvest->PrepareFall(Resource);}
    TryNetworkFall();
}

void AProductionFallingTree::TryNetworkFall()
{
    auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>();if(!Harvest||!NetFall.Valid||bFallReady)return;
    FProductionResource Resource;Resource.Mesh=NetFall.Mesh;Resource.Layer=0;Resource.Transform=NetFall.Transform;
    Resource.Seed=NetFall.Seed;Resource.Direction=NetFall.Plan.Direction;
    const int32 Variant=ProductionHarvestAssets::TreeVariant(Resource.Mesh);
    if(Variant==INDEX_NONE)return;
    // Several nearby falls can share a variant. Another fall may release the
    // preload handle after assigning its mesh, while that mesh remains loaded.
    if(!ProductionHarvestAssets::FallingMesh(Variant).ResolveObject())
    {Harvest->PrepareFall(Resource);return;}
    const double Now=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    Elapsed=float(FMath::Max(0.,Now-NetFall.StartedAt));
    // Do not replay old impact sounds/bursts when becoming relevant after impact.
    Landed=Elapsed>=NetFall.Plan.AnticipationSeconds+NetFall.Plan.FallSeconds;
    const float Phase=FMath::Clamp((Elapsed-NetFall.Plan.AnticipationSeconds)/NetFall.Plan.FallSeconds,0.f,1.f);
    CrownTouched=FMath::Lerp(1.2f,NetFall.Plan.LandingAngle,FMath::Pow(Phase,1.9f))>=NetFall.Plan.CrownAngle;
    InitializeFall(Resource,Resource.Direction);Harvest->ReleasePreparedFall(Resource);
}
