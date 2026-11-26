#include "FacilityHallEncounter.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HangingBellM09.h"
#include "../Monsters/M09CeilingRoute.h"
#include "../Monsters/VortexCofferM25.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
constexpr int32 PowerResearcher=0, PowerTechnician=1, PowerBell=2, PowerCoffer=3;
float PowerFootprint(int32 Member) { return Member==PowerCoffer ? 225.f : Member==PowerBell ? 85.f : 44.f; }
// Production module coordinates, UE centimetres. The raised maintenance aisle is z=240.
const FBox PowerSwitchgearFloors[]={
    FBox(FVector(-850,-210,0),FVector(850,210,0)),
    FBox(FVector(-260,-1040,0),FVector(260,-210,0))
};
const FBox PowerGeneratorFloors[]={
    FBox(FVector(-1260,-190,0),FVector(1260,190,0)),
    FBox(FVector(-1240,190,0),FVector(-600,970,0)),
    FBox(FVector(600,190,0),FVector(1240,970,0)),
    FBox(FVector(-940,-1025,240),FVector(940,-765,240))
};
// Probe below the high roof, away from the low maintenance platform and door sleeves.
const FVector PowerGeneratorCeilings[]={FVector(-850,-100,50),FVector(850,-100,50),FVector(-850,650,50),FVector(850,650,50)};
const FVector PowerControlCeilings[]={FVector(-1100,850,50),FVector(1100,850,50)};
}

bool AFacilityHallEncounter::IsPower(const FString& Module)
{
    return Module==TEXT("SwitchgearGallery") || Module==TEXT("GeneratorHall") || Module==TEXT("AccumulatorControl");
}

TArray<FString> AFacilityHallEncounter::PowerMonsterClassPaths()
{
    return {
        TEXT("/Game/Monsters/FacelessResearcher/BP_FacelessResearcher.BP_FacelessResearcher_C"),
        TEXT("/Game/Monsters/CargoTechnician/BP_CargoTechnician.BP_CargoTechnician_C"),
        TEXT("/Script/FPSGAME.HangingBellM09"),
        TEXT("/Game/Monsters/VortexCofferM25/BP_VortexCofferM25.BP_VortexCofferM25_C")
    };
}

bool AFacilityHallEncounter::IsPowerBossDefeated() const
{
    return Slots.IsValidIndex(PowerBossSlot) && Slots[PowerBossSlot].bDefeated;
}

void AFacilityHallEncounter::ConfigurePower()
{
    const UClass* Expected[]={ANurseZombie::StaticClass(),ANurseZombie::StaticClass(),AHangingBellM09::StaticClass(),AVortexCofferM25::StaticClass()};
    for (const FString& Path:PowerMonsterClassPaths())
    {
        UClass* Class=FSoftClassPath(Path).ResolveClass();
        if (!Class || !Class->IsChildOf(Expected[Members.Num()]))
        { UE_LOG(LogTemp,Error,TEXT("[PowerEncounter] Missing prepared class %s"),*Path); return; }
        Members.Add(Class);
    }
    const uint32 Salt=Run->NodeRandomSalt(Room.Id);
    FRandomStream Composition(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnComposition ^ Salt)));
    Placement.Initialize(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnPlacement ^ Salt)));
    const bool Control=Room.Module==TEXT("AccumulatorControl"),GeneratorHall=Room.Module==TEXT("GeneratorHall");
    if (Control)
    {
        // The real boss slot is eligible on area entry, independent of ordinary kills.
        PowerBossSlot=Slots.Num();auto& Boss=Slots.AddDefaulted_GetRef();Boss.Member=PowerCoffer;Boss.bPowerBoss=true;
    }
    const int32 BellCount=Control ? 2 : GeneratorHall ? 4 : 0;
    for (int32 I=0;I<BellCount;++I)
    { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=PowerBell;Slot.bCeiling=true;Slot.PowerPosition=I; }
    const int32 StaffCount=Control ? 0 : Composition.RandRange(6,8);
    for (int32 I=0;I<StaffCount;++I)
    {
        auto& Slot=Slots.AddDefaulted_GetRef();
        Slot.Member=I<2 ? I : Composition.RandRange(PowerResearcher,PowerTechnician);
        Slot.PowerPosition=I;
    }
    FirstWaveCount=Slots.Num();bSecondWave=true; // Fixed single wave; no maintenance-door additions.
    GetWorldTimerManager().SetTimer(EncounterTimer,this,&AFacilityHallEncounter::UpdateEncounter,.2f,true);
    UE_LOG(LogTemp,Log,TEXT("[PowerEncounter] %s staff=%d bells=%d vortex_coffer=%d initial_count=%d"),
        *Room.Module,StaffCount,BellCount,Control?1:0,FirstWaveCount);
}

bool AFacilityHallEncounter::FindPowerSpawn(const FFacilityHallSlot& Slot,const ACharacter* Defaults,FVector& Location,FRotator& Facing)
{
    const FTransform Transform(FRotator(0,Room.Yaw,0),Room.Origin);
    const bool GeneratorHall=Room.Module==TEXT("GeneratorHall");
    const float Radius=FMath::Max(PowerFootprint(Slot.Member),Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius());
    for (int32 Attempt=0;Attempt<12;++Attempt)
    {
        FVector Local;
        if (Slot.bPowerBoss)
        {
            // Center positions in the existing south apron walk mask. Keep the full
            // 4.5 m body outside the central 7.4 m core and inside the upper ring.
            Local=Attempt==0 ? FVector(0,800,0)
                : FVector(Placement.FRandRange(-850.f,850.f),Placement.FRandRange(700.f,900.f),0);
        }
        else if (Slot.bCeiling)
        {
            Local=GeneratorHall ? PowerGeneratorCeilings[Slot.PowerPosition] : PowerControlCeilings[Slot.PowerPosition];
            if (Attempt>0)Local+=FVector(Placement.FRandRange(-100.f,100.f),Placement.FRandRange(-100.f,100.f),0);
        }
        else
        {
            const FBox& Floor=GeneratorHall ? PowerGeneratorFloors[Slot.PowerPosition%UE_ARRAY_COUNT(PowerGeneratorFloors)]
                : PowerSwitchgearFloors[Slot.PowerPosition%UE_ARRAY_COUNT(PowerSwitchgearFloors)];
            const float Margin=Radius+25.f;
            Local=FVector(Placement.FRandRange(Floor.Min.X+Margin,Floor.Max.X-Margin),
                Placement.FRandRange(Floor.Min.Y+Margin,Floor.Max.Y-Margin),Floor.Min.Z);
        }
        const FVector Candidate=Transform.TransformPosition(Local);
        bool Occupied=false;
        for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if (const APawn* Player=It->Get() ? It->Get()->GetPawn().Get() : nullptr)
                Occupied |= (Slot.bCeiling || FMath::Abs(Player->GetNavAgentLocation().Z-Candidate.Z)<180.f)
                    && FVector::DistSquared2D(Player->GetActorLocation(),Candidate)<FMath::Square(Slot.bPowerBoss ? 600. : 450.);
        for (const auto& Other:Slots) if (Other.Monster.IsValid() && Slot.bCeiling==Other.bCeiling)
            Occupied |= (Slot.bCeiling || FMath::Abs(Other.Monster->GetNavAgentLocation().Z-Candidate.Z)<120.f)
                && FVector::DistSquared2D(Other.Monster->GetActorLocation(),Candidate)
                    <FMath::Square(Slot.bCeiling ? 550.f : Radius+PowerFootprint(Other.Member)+80.f);
        if (Occupied)continue;
        if (Slot.bCeiling)
        {
            FVector Contact;AM09CeilingRoute* Route=nullptr;
            if (!AM09CeilingRoute::FindPlacement(GetWorld(),Candidate,this,Contact,Route)
                || Room.DistanceSquared(Contact)>FMath::Square(20.))continue;
            Location=Contact-FVector(0,0,143);
        }
        else if (!FindSpawn(Defaults,Candidate,Location,Radius))continue;
        Facing=FRotator(0,Room.Yaw+(Slot.bPowerBoss ? -90.f : Placement.FRandRange(-180.f,180.f)),0);
        return true;
    }
    // Retry the same assigned slot; no forced overlap and no completion on failure.
    return false;
}
