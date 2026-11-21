#include "VillageBuildDefense.h"
#include "VoxelBuildPalette.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

AVillageDefenseSection* VillageBuildDefense::SpawnPlaced(const FVoxelBuildPrefab& Definition,
    ATemperateHillsWorld& Hills,const FGuid& InstanceId,const FTransform& Pose)
{
    UWorld* World=Hills.GetWorld();
    UClass* LogicClass=Definition.ActorClass.LoadSynchronous();
    if(!World||!Hills.HasAuthority()||!InstanceId.IsValid()||!LogicClass||
        !LogicClass->IsChildOf(AVillageDefenseSection::StaticClass())||!Definition.Mesh.LoadSynchronous())
        return nullptr;
    // The catalog mesh is the stone frame; the moving grid blocks passage as
    // soon as the placement succeeds, even on a host that never previewed it.
    if(Definition.Id==StoneGate&&!AHighVillageGate::PlacedGrilleMeshPath().TryLoad())
        return nullptr;
    auto* Defense=World->SpawnActorDeferred<AVillageDefenseSection>(LogicClass,Pose,&Hills,nullptr,
        ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!Defense)return nullptr;
    const int32 SectionId=GetTypeHash(InstanceId)&MAX_int32;
    if(auto* HighGate=Cast<AHighVillageGate>(Defense))
        HighGate->InitializeHighGate(&Hills,SectionId,false,InstanceId);
    else if(auto* Wall=Cast<AHighVillageWall>(Defense))
        Wall->InitializeHighWall(&Hills,SectionId,InstanceId);
    else if(auto* TimberGate=Cast<AVillageDefenseGate>(Defense))
        TimberGate->InitializeGate(&Hills,SectionId,false,InstanceId);
    else
        Defense->Initialize(&Hills,SectionId,Definition.Mesh.ToSoftObjectPath(),1200.f,InstanceId);
    Defense->FinishSpawning(Pose);
    return Defense;
}
