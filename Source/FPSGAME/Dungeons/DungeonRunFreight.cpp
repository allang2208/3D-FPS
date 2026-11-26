#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "Engine/World.h"

void UDungeonRunSubsystem::BindFreightTheme(AAuthoredDungeonGenerator* InGenerator)
{
    TArray<int32> FreightRooms;
    for (const auto& Node:Nodes)
        if (AFacilityHallEncounter::IsFreight(Node.Module)) FreightRooms.Add(Node.Id);
    if (FreightRooms.IsEmpty()) return;
    TArray<int32> AreaRooms=FreightRooms;
    for (const auto& Node:Nodes) if (Node.bConnector)
    {
        TArray<int32> Neighbors;CollectNeighborRooms(Node.Id,Neighbors);
        if (Neighbors.Num()>=2 && !Neighbors.ContainsByPredicate([&FreightRooms](int32 Id){return !FreightRooms.Contains(Id);}))
            AreaRooms.Add(Node.Id);
    }
    IncludeTreasureSideRooms(AreaRooms);
    TArray<FDungeonRunDoor> Boundaries;
    for (const auto& Node:Nodes) if (FreightRooms.Contains(Node.Id))
    {
        // Real door transforms and membership identify the two external ends,
        // even when layout search assembles a theme in the reverse direction.
        for (const auto& Door:Node.Doors)
            if (!AreaRooms.Contains(Door.Neighbor)&&!IsOptionalSideNode(Door.Neighbor)) Boundaries.Add(Door);
    }
    if (FreightRooms.Num()==3 && Boundaries.Num()==2)
    {
        FActorSpawnParameters Params;Params.Owner=InGenerator;Params.ObjectFlags|=RF_Transient;
        auto* Area=GetWorld()->SpawnActor<ADungeonThemeEncounter>(ADungeonThemeEncounter::StaticClass(),FTransform::Identity,Params);
        if (Area && Area->Configure(this,InGenerator,AreaRooms,Boundaries,EDungeonThemeObjective::FreightBoss)) FreightTheme=Area;
        else if (Area) Area->Destroy();
    }
    if (!FreightTheme.IsValid())
        UE_LOG(LogTemp,Error,TEXT("[FreightEncounter] Expected three freight rooms and two outer boundaries; rooms=%d boundaries=%d"),FreightRooms.Num(),Boundaries.Num());
}

bool UDungeonRunSubsystem::IsFreightBossDefeated() const
{
    if (!bActive || !Generator.IsValid()) return false;
    if (GetWorld()->GetNetMode()==NM_Client) return bNetworkFreightBossDefeated;
    for (const auto& Encounter:HallEncounters)
        if (Encounter.IsValid() && Encounter->IsFreightBossDefeated()) return true;
    return false;
}
