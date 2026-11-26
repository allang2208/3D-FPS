#include "FacilityHallEncounter.h"
#include "../Monsters/RootCrownRigPreview.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/SpiralPillarM14.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
constexpr int32 Gardener=0,Spiral=1,Crown=2;
float Footprint(int32 Member) { return Member==Crown ? 225.f : Member==Spiral ? 125.f : 44.f; }
// Room-local UE centimetres. These are dry floors; Blender source Y is negated.
const FBox NurseryFloors[]={
    FBox(FVector(-1100,100,0),FVector(1050,650,0)),
    FBox(FVector(-950,-220,0),FVector(950,100,0)),
    FBox(FVector(-550,-680,0),FVector(950,-250,0))
};
const FBox HydroFloors[]={
    FBox(FVector(-1950,-150,0),FVector(-1250,950,0)),
    FBox(FVector(1250,-150,0),FVector(1950,950,0)),
    FBox(FVector(-1150,650,0),FVector(1150,980,0)),
    FBox(FVector(-1300,-1400,240),FVector(1300,-1000,240))
};
const FVector HydroSpirals[]={FVector(-1575,450,0),FVector(1575,450,0),FVector(-650,800,0),FVector(650,800,0)};
const FVector BiosphereSpirals[]={FVector(-1000,1300,0),FVector(1000,1300,0)};
const FVector SpiralJitter(85,65,0);
const FBox BiosphereCrownFloor(FVector(-1900,-450,0),FVector(-1550,-80,0));

void AddEcologySpawnFloor(TArray<FBox>& Cells,const FTransform& Transform,const FBox& Floor)
{
    // Match FindSpawn's floor-height tolerance, including the hydroponics balcony.
    const FVector HeightTolerance(0,0,40);
    Cells.Add(FBox(Floor.Min-HeightTolerance,Floor.Max+HeightTolerance).TransformBy(Transform));
}
}

bool AFacilityHallEncounter::IsEcology(const FString& Module)
{
    return Module==TEXT("EcoNursery") || Module==TEXT("EcoHydroponics") || Module==TEXT("EcoBiosphere");
}

TArray<FString> AFacilityHallEncounter::EcologyMonsterClassPaths()
{
    return {
        TEXT("/Game/Monsters/EcologyGardener/BP_EcologyGardener.BP_EcologyGardener_C"),
        TEXT("/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14.BP_SpiralPillarM14_C"),
        TEXT("/Game/Monsters/RootCrown/BP_RootCrownRigPreview.BP_RootCrownRigPreview_C")
    };
}

bool AFacilityHallEncounter::IsEcologyBossDefeated() const
{
    return Slots.IsValidIndex(EcologyBossSlot) && Slots[EcologyBossSlot].bDefeated;
}

void AFacilityHallEncounter::ConfigureEcology()
{
    const UClass* Expected[]={ANurseZombie::StaticClass(),ASpiralPillarM14::StaticClass(),ARootCrownRigPreview::StaticClass()};
    for (const FString& Path:EcologyMonsterClassPaths())
    {
        UClass* Class=FSoftClassPath(Path).ResolveClass();
        if (!Class || !Class->IsChildOf(Expected[Members.Num()]))
        { UE_LOG(LogTemp,Error,TEXT("[EcologyEncounter] Missing prepared class %s"),*Path); return; }
        Members.Add(Class);
    }
    const uint32 Salt=Run->NodeRandomSalt(Room.Id);
    FRandomStream Composition(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnComposition ^ Salt)));
    Placement.Initialize(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnPlacement ^ Salt)));
    const bool Biosphere=Room.Module==TEXT("EcoBiosphere"),Hydro=Room.Module==TEXT("EcoHydroponics");
    // The catalog walk_mask reserves the through-route (only y=-150..150 cm).
    // It is not the encounter's spawn area: the authored dry aisles, balcony,
    // rear spiral positions and crown apron deliberately lie outside that lane.
    // Change only this encounter's room copy; route/navigation masks and every
    // FindSpawn ground, room-boundary, support, capsule and nav-data check remain.
    Room.WalkCells.Reset();
    const FTransform RoomTransform(FRotator(0,Room.Yaw,0),Room.Origin);
    if (Biosphere)
    {
        AddEcologySpawnFloor(Room.WalkCells,RoomTransform,BiosphereCrownFloor);
        for (const FVector& Anchor:BiosphereSpirals)
            AddEcologySpawnFloor(Room.WalkCells,RoomTransform,FBox(Anchor-SpiralJitter,Anchor+SpiralJitter));
    }
    else if (Hydro)
    {
        for (const FBox& Floor:HydroFloors) AddEcologySpawnFloor(Room.WalkCells,RoomTransform,Floor);
    }
    else
    {
        for (const FBox& Floor:NurseryFloors) AddEcologySpawnFloor(Room.WalkCells,RoomTransform,Floor);
    }
    if (Biosphere)
    {
        EcologyBossSlot=Slots.Num();auto& Boss=Slots.AddDefaulted_GetRef();Boss.Member=Crown;Boss.bEcologyBoss=true;
    }
    const int32 SpiralCount=Biosphere ? 2 : Hydro ? 4 : 0;
    for (int32 I=0;I<SpiralCount;++I)
    { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=Spiral;Slot.EcologyPosition=I; }
    const int32 GardenerCount=Biosphere ? 0 : Composition.RandRange(6,8);
    for (int32 I=0;I<GardenerCount;++I)
    { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=Gardener;Slot.EcologyPosition=I; }
    FirstWaveCount=Slots.Num();bSecondWave=true;
    GetWorldTimerManager().SetTimer(EncounterTimer,this,&AFacilityHallEncounter::UpdateEncounter,.2f,true);
    UE_LOG(LogTemp,Log,TEXT("[EcologyEncounter] %s gardeners=%d spirals=%d root_crown=%d single_wave=1"),*Room.Module,GardenerCount,SpiralCount,Biosphere?1:0);
}

bool AFacilityHallEncounter::FindEcologySpawn(const FFacilityHallSlot& Slot,const ACharacter* Defaults,FVector& Location,FRotator& Facing)
{
    const FTransform Transform(FRotator(0,Room.Yaw,0),Room.Origin);
    const float Radius=Footprint(Slot.Member);
    const bool Hydro=Room.Module==TEXT("EcoHydroponics");
    // UE centimetres (authoring Blender Y is negated). This broad ground-floor
    // apron is west of the garden, east of the entry, and south of the office.
    // Keep the 4.5 m footprint clear of the stair at x=-1220, trees and upper chest.
    // Try the authored center first, then retry within the same clear apron.
    for (int32 Attempt=0;Attempt<12;++Attempt)
    {
        FVector Local;
        if (Slot.bEcologyBoss)
            Local=Attempt==0 ? FVector(-1725,-250,0)
                : FVector(Placement.FRandRange(BiosphereCrownFloor.Min.X,BiosphereCrownFloor.Max.X),
                    Placement.FRandRange(BiosphereCrownFloor.Min.Y,BiosphereCrownFloor.Max.Y),BiosphereCrownFloor.Min.Z);
        else if (Slot.Member==Spiral)
        {
            Local=Hydro ? HydroSpirals[Slot.EcologyPosition] : BiosphereSpirals[Slot.EcologyPosition];
            if (Attempt>0) Local+=FVector(Placement.FRandRange(-SpiralJitter.X,SpiralJitter.X),Placement.FRandRange(-SpiralJitter.Y,SpiralJitter.Y),0);
        }
        else
        {
            const FBox& Floor=Hydro ? HydroFloors[Slot.EcologyPosition%UE_ARRAY_COUNT(HydroFloors)]
                : NurseryFloors[Slot.EcologyPosition%UE_ARRAY_COUNT(NurseryFloors)];
            const float Margin=Radius+25.f;
            Local=FVector(Placement.FRandRange(Floor.Min.X+Margin,Floor.Max.X-Margin),
                Placement.FRandRange(Floor.Min.Y+Margin,Floor.Max.Y-Margin),Floor.Min.Z);
        }
        const FVector Candidate=Transform.TransformPosition(Local);
        bool Occupied=false;
        for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if (const APawn* Player=It->Get() ? It->Get()->GetPawn().Get() : nullptr)
                Occupied |= FMath::Abs(Player->GetNavAgentLocation().Z-Candidate.Z)<180.f
                    && FVector::DistSquared2D(Player->GetActorLocation(),Candidate)<FMath::Square(Slot.bEcologyBoss ? 600. : 450.);
        for (const auto& Other:Slots) if (Other.Monster.IsValid())
            Occupied |= FMath::Abs(Other.Monster->GetNavAgentLocation().Z-Candidate.Z)<120.f
                && FVector::DistSquared2D(Other.Monster->GetActorLocation(),Candidate)<FMath::Square(Radius+Footprint(Other.Member)+80.f);
        if (Occupied || !FindSpawn(Defaults,Candidate,Location,Radius)) continue;
        Facing=FRotator(0,Room.Yaw+(Slot.bEcologyBoss ? 0.f : Placement.FRandRange(-180.f,180.f)),0);
        return true;
    }
    // No forced spawn through geometry, and failed placement never counts as a kill.
    return false;
}
