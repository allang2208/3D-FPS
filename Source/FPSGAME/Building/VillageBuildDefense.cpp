#include "VillageBuildDefense.h"
#include "VoxelBuildPalette.h"
#include "../WorldGeneration/VillageLightningSpire.h"
#include "../WorldGeneration/VillageSmartTurret.h"
#include "../WorldGeneration/VillageSiegeEngine.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

VillageBuildDefense::ETier VillageBuildDefense::UnlockedTier(const ATemperateHillsWorld* Hills)
{
    if(!Hills||!Hills->IsVillageWallRepaired())return ETier::None;
    if(!Hills->HasVillageHighWall())return ETier::RepairedWall;
    static const FName TowerPlan(TEXT("village_construction"));
    if(!Hills->IsVillagePlanUnlocked(TowerPlan))return ETier::HighCurtain;
    return Hills->IsVillagePlanUnlocked(MechanicsPlan)?ETier::Mechanics:ETier::Fortifications;
}

const TCHAR* VillageBuildDefense::ProjectName(ETier Tier)
{
    switch(Tier)
    {
    case ETier::RepairedWall:return TEXT("修复城墙");
    case ETier::HighCurtain:return TEXT("升级高墙");
    case ETier::Fortifications:return TEXT("防御工事");
    case ETier::Mechanics:return TEXT("守备机械");
    default:return TEXT("");
    }
}

FString VillageBuildDefense::LockReason(ETier Tier)
{
    return FString::Printf(TEXT("请先在修女处完成「%s」"),ProjectName(Tier));
}

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
    if(Definition.Id==StoneGate && (!AHighVillageGate::PlacedGrilleMeshPath().TryLoad() || !AHighVillageGate::ReleaseMeshPath().TryLoad()))
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
    else if(auto* Spire=Cast<AVillageLightningSpire>(Defense))
        Spire->Initialize(&Hills,SectionId,AVillageLightningSpire::MeshAsset(TEXT("Base")),850.f,InstanceId);
    else if(auto* Turret=Cast<AVillageSmartTurret>(Defense))
        Turret->Initialize(&Hills,SectionId,AVillageSmartTurret::MeshAsset(TEXT("Base")),900.f,InstanceId);
    else if(auto* Siege=Cast<AVillageSiegeEngine>(Defense))
        Siege->Initialize(&Hills,SectionId,AVillageSiegeEngine::MeshAsset(
            Definition.Id==Trebuchet?TEXT("TrebuchetBase"):TEXT("BallistaBase")),Definition.Id==Trebuchet?1100.f:680.f,InstanceId);
    else
        Defense->Initialize(&Hills,SectionId,Definition.Mesh.ToSoftObjectPath(),1200.f,InstanceId);
    Defense->FinishSpawning(Pose);
    return Defense;
}
