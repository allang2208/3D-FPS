#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonShortcutGate.h"
#include "FacilityHallEncounter.h"
#include "Engine/World.h"

bool UDungeonRunSubsystem::IsOptionalSideNode(int32 Id) const
{
    const auto* Node=NodeById(Id);
    return Node&&(Node->Route.StartsWith(TEXT("Loop."))||Node->Route.Contains(TEXT("_Treasure")));
}

void UDungeonRunSubsystem::IncludeTreasureSideRooms(TArray<int32>& AreaRooms) const
{
    for(int32 I=0;I<AreaRooms.Num();++I)
        if(const auto* Node=NodeById(AreaRooms[I]))for(int32 Neighbor:Node->Neighbors)
            if(const auto* Side=NodeById(Neighbor);Side&&Side->Route.Contains(TEXT("_Treasure")))AreaRooms.AddUnique(Neighbor);
}

bool UDungeonRunSubsystem::AreRouteObjectivesDefeated(const FString& Route) const
{
    if(!bActive)return false;
    int32 ThemedRooms=0;
    for(const auto& Node:Nodes)if(Node.Route==Route)
    {
        bool Passed=false;
        if(AFacilityHallEncounter::IsMedical(Node.Module))Passed=IsMedicalBossDefeated();
        else if(AFacilityHallEncounter::IsFreight(Node.Module))Passed=IsFreightBossDefeated();
        else if(AFacilityHallEncounter::IsEcology(Node.Module))Passed=IsEcologyBossDefeated();
        else if(AFacilityHallEncounter::IsPower(Node.Module))Passed=IsPowerBossDefeated();
        else if(AFacilityHallEncounter::IsIncineration(Node.Module))Passed=IsIncinerationBossDefeated();
        else if(AFacilityHallEncounter::IsStaffLiving(Node.Module))Passed=IsStaffLivingBossDefeated();
        else continue;
        ++ThemedRooms;if(!Passed)return false;
    }
    return ThemedRooms>0;
}

bool UDungeonRunSubsystem::BindReturnLinks(AAuthoredDungeonGenerator* InGenerator)
{
    TSet<FString> Links;
    for(const auto& Node:Nodes)if(Node.Route.StartsWith(TEXT("Loop.")))Links.Add(Node.Route);
    for(const FString& Link:Links)
    {
        TArray<FDungeonRunDoor> Doors;TArray<FString> Routes;
        for(const auto& Node:Nodes)if(!Node.Route.StartsWith(TEXT("Loop.")))
            for(const auto& Door:Node.Doors)
                if(const auto* Neighbor=NodeById(Door.Neighbor);Neighbor&&Neighbor->Route==Link)
                {Doors.Add(Door);Routes.Add(Node.Route);}
        if(Doors.Num()!=2)return false;
        for(const auto& Door:Doors)
        {
            FActorSpawnParameters Params;Params.Owner=InGenerator;Params.ObjectFlags|=RF_Transient;
            auto* Gate=GetWorld()->SpawnActor<ADungeonShortcutGate>(ADungeonShortcutGate::StaticClass(),FTransform::Identity,Params);
            if(!Gate)return false;
            ReturnLinkGates.Add(Gate);
            if(!Gate->ConfigureReturnLink(this,Door,Routes[0],Routes[1]))return false;
        }
    }
    return true;
}
