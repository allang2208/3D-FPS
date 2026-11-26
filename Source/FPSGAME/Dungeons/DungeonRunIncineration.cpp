#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "Engine/World.h"

void UDungeonRunSubsystem::BindIncinerationTheme(AAuthoredDungeonGenerator* InGenerator)
{
    TArray<int32> IncinerationRooms;
    for (const auto& Node:Nodes)
        if (AFacilityHallEncounter::IsIncineration(Node.Module)) IncinerationRooms.Add(Node.Id);
    if (IncinerationRooms.IsEmpty())return;
    TArray<int32> AreaRooms=IncinerationRooms;
    for (const auto& Node:Nodes)if (Node.bConnector)
    {
        TArray<int32> Neighbors;CollectNeighborRooms(Node.Id,Neighbors);
        if (Neighbors.Num()>=2 && !Neighbors.ContainsByPredicate([&IncinerationRooms](int32 Id){return !IncinerationRooms.Contains(Id);}))
            AreaRooms.Add(Node.Id);
    }
    IncludeTreasureSideRooms(AreaRooms);
    TArray<FDungeonRunDoor> Boundaries;
    for (const auto& Node:Nodes)if (IncinerationRooms.Contains(Node.Id))
        for (const auto& Door:Node.Doors)if (!AreaRooms.Contains(Door.Neighbor)&&!IsOptionalSideNode(Door.Neighbor))Boundaries.Add(Door);
    if (IncinerationRooms.Num()==3 && Boundaries.Num()==2)
    {
        FActorSpawnParameters Params;Params.Owner=InGenerator;Params.ObjectFlags|=RF_Transient;
        auto* Area=GetWorld()->SpawnActor<ADungeonThemeEncounter>(ADungeonThemeEncounter::StaticClass(),FTransform::Identity,Params);
        if (Area && Area->Configure(this,InGenerator,AreaRooms,Boundaries,EDungeonThemeObjective::IncinerationBoss))IncinerationTheme=Area;
        else if (Area)Area->Destroy();
    }
    if (!IncinerationTheme.IsValid())
        UE_LOG(LogTemp,Error,TEXT("[IncinerationEncounter] Expected three treatment rooms and two boundaries; rooms=%d boundaries=%d"),IncinerationRooms.Num(),Boundaries.Num());
}

bool UDungeonRunSubsystem::IsIncinerationBossDefeated() const
{
    if (!bActive || !Generator.IsValid())return false;
    if (GetWorld()->GetNetMode()==NM_Client)return bNetworkIncinerationBossDefeated;
    for (const auto& Encounter:HallEncounters)
        if (Encounter.IsValid() && Encounter->IsIncinerationBossDefeated())return true;
    return false;
}
