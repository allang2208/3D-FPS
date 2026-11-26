#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "Engine/World.h"

void UDungeonRunSubsystem::BindPowerTheme(AAuthoredDungeonGenerator* InGenerator)
{
    TArray<int32> PowerRooms;
    for (const auto& Node:Nodes)
        if (AFacilityHallEncounter::IsPower(Node.Module)) PowerRooms.Add(Node.Id);
    if (PowerRooms.IsEmpty()) return;
    TArray<int32> AreaRooms=PowerRooms;
    for (const auto& Node:Nodes) if (Node.bConnector)
    {
        TArray<int32> Neighbors;CollectNeighborRooms(Node.Id,Neighbors);
        if (Neighbors.Num()>=2 && !Neighbors.ContainsByPredicate([&PowerRooms](int32 Id){return !PowerRooms.Contains(Id);}))
            AreaRooms.Add(Node.Id);
    }
    IncludeTreasureSideRooms(AreaRooms);
    TArray<FDungeonRunDoor> Boundaries;
    for (const auto& Node:Nodes) if (PowerRooms.Contains(Node.Id))
    {
        // Real door transforms and membership identify the two external ends,
        // even when layout search assembles a theme in the reverse direction.
        for (const auto& Door:Node.Doors)
            if (!AreaRooms.Contains(Door.Neighbor)&&!IsOptionalSideNode(Door.Neighbor)) Boundaries.Add(Door);
    }
    if (PowerRooms.Num()==3 && Boundaries.Num()==2)
    {
        FActorSpawnParameters Params;Params.Owner=InGenerator;Params.ObjectFlags|=RF_Transient;
        auto* Area=GetWorld()->SpawnActor<ADungeonThemeEncounter>(ADungeonThemeEncounter::StaticClass(),FTransform::Identity,Params);
        if (Area && Area->Configure(this,InGenerator,AreaRooms,Boundaries,EDungeonThemeObjective::PowerBoss)) PowerTheme=Area;
        else if (Area) Area->Destroy();
    }
    if (!PowerTheme.IsValid())
        UE_LOG(LogTemp,Error,TEXT("[PowerEncounter] Expected three power rooms and two outer boundaries; rooms=%d boundaries=%d"),PowerRooms.Num(),Boundaries.Num());
}

bool UDungeonRunSubsystem::IsPowerBossDefeated() const
{
    if (!bActive || !Generator.IsValid()) return false;
    if (GetWorld()->GetNetMode()==NM_Client) return bNetworkPowerBossDefeated;
    for (const auto& Encounter:HallEncounters)
        if (Encounter.IsValid() && Encounter->IsPowerBossDefeated()) return true;
    return false;
}
