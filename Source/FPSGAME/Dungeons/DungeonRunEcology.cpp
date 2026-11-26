#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "Engine/World.h"

void UDungeonRunSubsystem::BindEcologyTheme(AAuthoredDungeonGenerator* InGenerator)
{
    TArray<int32> EcologyRooms;
    for (const auto& Node:Nodes)
        if (AFacilityHallEncounter::IsEcology(Node.Module)) EcologyRooms.Add(Node.Id);
    if (EcologyRooms.IsEmpty()) return;
    TArray<int32> AreaRooms=EcologyRooms;
    // Follow complete connector chains; internal sleeves/stairs stay in the
    // same area even if the generated route reverses this theme's orientation.
    for (const auto& Node:Nodes) if (Node.bConnector)
    {
        TArray<int32> Neighbors;CollectNeighborRooms(Node.Id,Neighbors);
        if (Neighbors.Num()>=2 && !Neighbors.ContainsByPredicate([&EcologyRooms](int32 Id){return !EcologyRooms.Contains(Id);}))
            AreaRooms.Add(Node.Id);
    }
    IncludeTreasureSideRooms(AreaRooms);
    TArray<FDungeonRunDoor> Boundaries;
    for (const auto& Node:Nodes) if (EcologyRooms.Contains(Node.Id))
        for (const auto& Door:Node.Doors)
            if (!AreaRooms.Contains(Door.Neighbor)&&!IsOptionalSideNode(Door.Neighbor)) Boundaries.Add(Door);
    if (EcologyRooms.Num()==3 && Boundaries.Num()==2)
    {
        FActorSpawnParameters Params;Params.Owner=InGenerator;Params.ObjectFlags|=RF_Transient;
        auto* Area=GetWorld()->SpawnActor<ADungeonThemeEncounter>(ADungeonThemeEncounter::StaticClass(),FTransform::Identity,Params);
        if (Area && Area->Configure(this,InGenerator,AreaRooms,Boundaries,EDungeonThemeObjective::EcologyBoss)) EcologyTheme=Area;
        else if (Area) Area->Destroy();
    }
    if (!EcologyTheme.IsValid())
        UE_LOG(LogTemp,Error,TEXT("[EcologyEncounter] Expected three ecology rooms and two outer boundaries; rooms=%d boundaries=%d"),EcologyRooms.Num(),Boundaries.Num());
}

bool UDungeonRunSubsystem::IsEcologyBossDefeated() const
{
    if (!bActive || !Generator.IsValid()) return false;
    if (GetWorld()->GetNetMode()==NM_Client) return bNetworkEcologyBossDefeated;
    for (const auto& Encounter:HallEncounters)
        if (Encounter.IsValid() && Encounter->IsEcologyBossDefeated()) return true;
    return false;
}
