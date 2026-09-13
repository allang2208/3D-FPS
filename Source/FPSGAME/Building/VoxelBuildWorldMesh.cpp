#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildRuntime.h"
#include "Async/Async.h"
#include "Components/DynamicMeshComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"

namespace
{
    TAutoConsoleVariable<int32> MeshWorkers(TEXT("fps.Building.MeshWorkers"),2,TEXT("Maximum in-flight static mesh jobs (1..4)."));
    TAutoConsoleVariable<int32> MeshApplies(TEXT("fps.Building.MeshAppliesPerFrame"),1,TEXT("Static mesh/collision commits per frame (1..8)."));
}

FVoxelBuildKey AVoxelBuildWorld::RenderKey(FVoxelBuildKey SourceChunk) const
{
    return {{},ChunkFor(ToCell(VolumeOrigin(SourceChunk.Volume)+CellMin(SourceChunk.Cell*16)))};
}

void AVoxelBuildWorld::RebuildAffected(const TArray<FVoxelEditCell>& Edit)
{
    TSet<FVoxelBuildKey> Keys;
    for(const auto& E:Edit)
        for(int32 Z=-1;Z<=1;++Z)for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
            Keys.Add({E.Volume,ChunkFor(E.Position+FIntVector(X,Y,Z))});
    TSet<FVoxelBuildKey> Groups;
    for(const auto& Source:Keys)
    {
        const auto Key=RenderKey(Source);Runtime->MeshGroups.FindOrAdd(Key).Add(Source);Groups.Add(Key);
    }
    for(const auto& Key:Groups){Runtime->DirtyChunks.Add(Key);++Runtime->MeshRevisions.FindOrAdd(Key);}
}

void AVoxelBuildWorld::TickMeshes()
{
    int32 Applied=0;const double Start=FPlatformTime::Seconds();
    for(int32 I=0;I<Runtime->MeshJobs.Num();)
    {
        auto& Job=Runtime->MeshJobs[I];
        if(!Job.Future.IsReady()){++I;continue;}
        auto Geometry=Job.Future.Get();
        if(Job.Revision==Runtime->MeshRevisions.FindRef(Job.Key))
        {
            ApplyChunk(Job.Key,MoveTemp(Geometry));Runtime->AppliedRevisions.Add(Job.Key,Job.Revision);++Applied;
        }
        Runtime->MeshJobs.RemoveAtSwap(I);
        if(Applied>=FMath::Clamp(MeshApplies.GetValueOnGameThread(),1,8)||FPlatformTime::Seconds()-Start>.0015)break;
    }
    const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);const FVector View=Pawn?Pawn->GetActorLocation():FVector::ZeroVector;
    while(Runtime->MeshJobs.Num()<FMath::Clamp(MeshWorkers.GetValueOnGameThread(),1,4)&&!Runtime->DirtyChunks.IsEmpty())
    {
        FVoxelBuildKey Key;double Best=TNumericLimits<double>::Max();bool Found=false;
        for(const auto& Candidate:Runtime->DirtyChunks)
        {
            if(Runtime->MeshJobs.ContainsByPredicate([&](const auto& Job){return Job.Key==Candidate;}))continue;
            const double Distance=FVector::DistSquared(View,VolumeOrigin(Candidate.Volume)+CellMin(Candidate.Cell*16)+FVector(160));
            if(Distance<Best){Best=Distance;Key=Candidate;Found=true;}
        }
        if(!Found)break;
        Runtime->DirtyChunks.Remove(Key);TArray<FVoxelChunkSnapshot> Inputs;TArray<FVoxelBuildKey> Empty;
        for(const auto& Source:Runtime->MeshGroups.FindChecked(Key))
        {
            FVoxelChunkSnapshot Input;Input.Origin=Source.Cell*16;
            Input.Offset=VolumeOrigin(Source.Volume)+CellMin(Input.Origin)-CellMin(Key.Cell*16);
            const auto* Free=FreeVolumes.Find(Source.Volume);const auto* Data=Source.Volume.IsValid()?(Free?&Free->Cells:nullptr):&Cells;
            bool Occupied=false;
            auto Add=[&](FIntVector Cell,FName Material)
            {
                const auto Local=Cell-Input.Origin;
                if(Local.X<-1||Local.Y<-1||Local.Z<-1||Local.X>16||Local.Y>16||Local.Z>16)return;
                if(const auto* Slot=MaterialSlots.Find(Material))
                {
                    Input.Slots.Add(Cell,*Slot);
                    Occupied|=Local.X>=0&&Local.Y>=0&&Local.Z>=0&&Local.X<16&&Local.Y<16&&Local.Z<16;
                }
            };
            // Small free volumes are read sparsely; do not scan an 18^3 halo
            // for every individually placed block in a spatial batch.
            if(Data&&Data->Num()<5832)for(const auto& C:*Data)Add(C.Key,C.Value);
            else if(Data)for(int32 Z=-1;Z<=16;++Z)for(int32 Y=-1;Y<=16;++Y)for(int32 X=-1;X<=16;++X)
            {
                const auto Cell=Input.Origin+FIntVector(X,Y,Z);if(const auto* M=Data->Find(Cell))Add(Cell,*M);
            }
            if(Occupied)Inputs.Add(MoveTemp(Input));else Empty.Add(Source);
        }
        for(const auto& Source:Empty)Runtime->MeshGroups.FindChecked(Key).Remove(Source);
        FVoxelMeshJob Job;Job.Key=Key;Job.Revision=Runtime->MeshRevisions.FindRef(Key);const double Radius=Palette->EdgeRadiusCm;
        Job.Future=Async(EAsyncExecution::ThreadPool,[Inputs=MoveTemp(Inputs),Radius]() mutable
        {return VoxelGeometry::Batch(MoveTemp(Inputs),Radius);});
        Runtime->MeshJobs.Add(MoveTemp(Job));
    }
}

void AVoxelBuildWorld::ApplyChunk(FVoxelBuildKey Key,TSharedPtr<FVoxelGeometry> Geometry)
{
    if(Geometry->Mesh.TriangleCount()==0&&Geometry->Collision.BoxElems.IsEmpty())
    {
        if(auto* Existing=Chunks.Find(Key)){(*Existing)->DestroyComponent();Chunks.Remove(Key);}
        return;
    }
    UDynamicMeshComponent* Component=Chunks.FindRef(Key);
    if(!Component)
    {
        Component=NewObject<UDynamicMeshComponent>(this);AddInstanceComponent(Component);Component->SetupAttachment(RootComponent);
        Component->SetRelativeLocation(VolumeOrigin(Key.Volume)+CellMin(Key.Cell*16));Component->SetMobility(EComponentMobility::Movable);
        Component->SetCollisionProfileName(TEXT("BlockAll"));Component->CollisionType=CTF_UseSimpleAsComplex;
        // UE's standard radial-damage overlap searches dynamic object channels.
        // The building is still non-simulating; only its query classification changes.
        Component->SetCollisionObjectType(ECC_WorldDynamic);
        Component->SetPhysMaterialOverride(StructuralContact);
        Component->bEnableComplexCollision=false;Component->SetDeferredCollisionUpdatesEnabled(true,false);
        Component->SetCanEverAffectNavigation(false);Component->SetGenerateOverlapEvents(false);
        Component->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
        Component->SetNotifyRigidBodyCollision(true);Component->OnComponentHit.AddDynamic(this,&AVoxelBuildWorld::OnBuildingHit);
        for(int32 I=0;I<SurfaceMaterials.Num();++I)Component->SetMaterial(I,SurfaceMaterials[I]);
        Component->RegisterComponent();Chunks.Add(Key,Component);
    }
    // Merged analytic boxes preserve exact voxel placement normals and avoid
    // triangle-mesh cooking during demolition. Interiors are also solid.
    Component->SetMesh(MoveTemp(Geometry->Mesh));
    Component->SetSimpleCollisionShapes(Geometry->Collision,true);
}
