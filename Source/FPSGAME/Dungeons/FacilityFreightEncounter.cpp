#include "FacilityHallEncounter.h"
#include "AuthoredDungeonGenerator.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
constexpr int32 Porter = 0, Technician = 1, Lurker = 2, Bellow = 3, Mawcrawler = 4;
// Authored centimetres, before room yaw/translation. The rail bed is x >= -550,
// |y| <= 525 at z=-180; all ground spawn boxes below are on dry platforms.
const FBox TransferFloors[] = {
    FBox(FVector(420,-1300,0),FVector(1380,-80,0)),
    FBox(FVector(60,-1770,60),FVector(1740,-1430,60))
};
const FBox WarehouseAisles[] = {
    FBox(FVector(-1400,700,0),FVector(230,1100,0)),
    FBox(FVector(-230,-550,0),FVector(230,650,0)),
    FBox(FVector(300,-700,0),FVector(1450,-300,0))
};
const FBox StationGround[] = {
    FBox(FVector(1400,-1080,0),FVector(2200,-550,0)),
    FBox(FVector(2200,-1080,0),FVector(3150,-550,0)),
    FBox(FVector(550,550,0),FVector(1250,1080,0)),
    FBox(FVector(2200,550,0),FVector(3150,1080,0))
};
const FBox StationBoss(FVector(300,-1100,0),FVector(1220,-550,0));
}

bool AFacilityHallEncounter::IsFreight(const FString& Module)
{
    return Module==TEXT("FreightTransfer_WarehouseLink") || Module==TEXT("AbandonedCargoWarehouse")
        || Module==TEXT("AbandonedTransitStation");
}

TArray<FString> AFacilityHallEncounter::FreightMonsterClassPaths()
{
    return {
        TEXT("/Game/Monsters/CargoPorter/BP_CargoPorter.BP_CargoPorter_C"),
        TEXT("/Game/Monsters/CargoTechnician/BP_CargoTechnician.BP_CargoTechnician_C"),
        TEXT("/Game/Monsters/LurkerM08/BP_LurkerM08.BP_LurkerM08_C"),
        TEXT("/Game/Monsters/BellowSacLobber/BP_BellowSacLobber.BP_BellowSacLobber_C"),
        TEXT("/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler.BP_M10Mawcrawler_C")
    };
}

bool AFacilityHallEncounter::IsFreightBossDefeated() const
{
    return Slots.IsValidIndex(FreightBossSlot) && Slots[FreightBossSlot].bDefeated;
}

void AFacilityHallEncounter::ConfigureFreight()
{
    for (const FString& Path:FreightMonsterClassPaths())
    {
        UClass* Class=FSoftClassPath(Path).ResolveClass();
        if (!Class || !Class->IsChildOf(ACharacter::StaticClass()))
        { UE_LOG(LogTemp,Error,TEXT("[FreightEncounter] Missing prepared class %s"),*Path); return; }
        Members.Add(Class);
    }
    const uint32 Salt=Run->NodeRandomSalt(Room.Id);
    FRandomStream Composition(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnComposition ^ Salt)));
    Placement.Initialize(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnPlacement ^ Salt)));
    if (Room.Module==TEXT("FreightTransfer_WarehouseLink"))
    {
        const int32 Count=Composition.RandRange(6,8);
        for (int32 I=0;I<Count;++I)
        { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=I<2 ? I : Composition.RandRange(Porter,Technician); }
    }
    else if (Room.Module==TEXT("AbandonedCargoWarehouse"))
    {
        for (int32 I=0;I<3;++I)
        { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=Lurker;Slot.FreightPosition=I; }
        const int32 StaffCount=Composition.RandRange(6,8);
        for (int32 I=0;I<StaffCount;++I)
        {
            auto& Slot=Slots.AddDefaulted_GetRef();
            Slot.Member=I<2 ? I : Composition.RandRange(Porter,Technician);
            Slot.FreightPosition=I%UE_ARRAY_COUNT(WarehouseAisles);
        }
    }
    else
    {
        // Boss owns a real slot from the outset; it does not wait for ordinary kills.
        FreightBossSlot=Slots.Num();
        auto& Boss=Slots.AddDefaulted_GetRef();Boss.Member=Mawcrawler;Boss.bFreightBoss=true;
        for (int32 I=0;I<4;++I)
        { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=Bellow;Slot.FreightPosition=I; }
        for (int32 I=0;I<4;++I)
        { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=Lurker;Slot.FreightPosition=I; }
    }
    FirstWaveCount=Slots.Num();bSecondWave=true;
    if(Room.Module==TEXT("AbandonedTransitStation"))ConfigureFreightReinforcements();
    GetWorldTimerManager().SetTimer(EncounterTimer,this,&AFacilityHallEncounter::UpdateEncounter,.2f,true);
    UE_LOG(LogTemp,Log,TEXT("[FreightEncounter] %s initial_count=%d reinforcement_cap=%d boss_slot=%d"),
        *Room.Module,FirstWaveCount,Slots.Num()-FirstWaveCount,FreightBossSlot);
}

bool AFacilityHallEncounter::FindFreightSpawn(const FFacilityHallSlot& Slot,const ACharacter* Defaults,FVector& Location,FRotator& Facing)
{
    const bool Station=Room.Module==TEXT("AbandonedTransitStation");
    const bool Upper=Station && Slot.Member==Bellow;
    const float Footprint=Slot.Member==Mawcrawler ? 225.f : Slot.Member==Lurker || Slot.Member==Bellow ? 135.f : 44.f;
    const double Margin=FMath::Max(Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius(),Footprint)+25.;
    const FTransform Transform(FRotator(0,Room.Yaw,0),Room.Origin);
    for (int32 Attempt=0;Attempt<12;++Attempt)
    {
        FBox Floor;
        if (Room.Module==TEXT("FreightTransfer_WarehouseLink")) Floor=TransferFloors[Placement.RandRange(0,1)];
        else if (!Station) Floor=WarehouseAisles[Slot.FreightPosition];
        else if (Slot.bFreightBoss) Floor=StationBoss;
        else if (Upper)
        {
            // Four separate bands of the same 5.4 m wide bridge at z=480 cm.
            // A failed upper-floor placement retries its band; no ground fallback.
            const double MinY=-1600.+Slot.FreightPosition*800.;
            Floor=FBox(FVector(2225,MinY,480),FVector(2765,MinY+800.,480));
        }
        else Floor=StationGround[Slot.FreightPosition];
        if (Floor.GetSize().X<=2*Margin || Floor.GetSize().Y<=2*Margin) continue;
        const FVector Local(Placement.FRandRange(Floor.Min.X+Margin,Floor.Max.X-Margin),
            Placement.FRandRange(Floor.Min.Y+Margin,Floor.Max.Y-Margin),Floor.Min.Z);
        // Exclude the complete rail corridor by the full footprint, not just the pivot.
        if (Station && !Upper && Local.X+Footprint>-550. && Local.X-Footprint<3800.
            && FMath::Abs(Local.Y)<525.+Footprint+20.) continue;
        const FVector Candidate=Transform.TransformPosition(Local);
        bool Occupied=false;
        for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if (const APawn* Player=It->Get() ? It->Get()->GetPawn().Get() : nullptr)
                Occupied |= FVector::DistSquared(Player->GetActorLocation(),Candidate)<FMath::Square(450.);
        for (const auto& Other:Slots)
        {
            if (!Other.Monster.IsValid()) continue;
            const FVector OtherFloor=Other.Monster->GetActorLocation()-FVector(0,0,Other.Monster->GetSimpleCollisionHalfHeight());
            if (FMath::Abs(OtherFloor.Z-Candidate.Z)>100.) continue;
            const float OtherFootprint=Other.Member==Mawcrawler ? 225.f : Other.Member==Lurker || Other.Member==Bellow ? 135.f : 44.f;
            Occupied |= FVector::DistSquared2D(OtherFloor,Candidate)<FMath::Square(Footprint+OtherFootprint+45.);
        }
        if (Occupied || !FindSpawn(Defaults,Candidate,Location,Footprint)) continue;
        Facing=FRotator(0,Room.Yaw+Placement.FRandRange(-180.f,180.f),0);
        if (Upper) Facing=Transform.TransformVectorNoScale(FVector(-1,0,0)).Rotation();
        return true;
    }
    return false;
}
