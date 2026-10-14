#include "FacilityHallEncounter.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonThemeEncounter.h"
#include "../Monsters/M09CeilingRoute.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
// Finished interior faces from MedicalOfficeWing20261010/author.py, in room-local cm.
// Consultation 01/02, records, shared doctors' office, chief office, clinical support.
const FBox MedicalOfficeRooms[] = {
    FBox(FVector(-886,-886,.6),FVector(-224,-14,.6)),
    FBox(FVector(-886,-1686,.6),FVector(-224,-914,.6)),
    FBox(FVector(-886,-2286,.6),FVector(-224,-1714,.6)),
    FBox(FVector(224,-866,.6),FVector(1686,-14,.6)),
    FBox(FVector(224,-2286,.6),FVector(946,-1334,.6)),
    FBox(FVector(974,-2286,.6),FVector(1686,-1334,.6))
};
}

bool AFacilityHallEncounter::IsMedical(const FString& Module)
{
    return Module == TEXT("MedicalDoctorOffice") || Module == TEXT("AbandonedIsolationWard")
        || Module == TEXT("AbandonedAnatomyTheatre");
}

TArray<FString> AFacilityHallEncounter::MedicalMonsterClassPaths()
{
    auto Paths = MonsterClassPaths();
    Paths.SetNum(3); // Same three ordinary staff, without the hall's Bellow additions.
    Paths.Add(TEXT("/Game/Monsters/MantisM27/BP_MantisM27.BP_MantisM27_C"));
    Paths.Add(TEXT("/Script/FPSGAME.HangingBellM09"));
    Paths.Add(TEXT("/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C"));
    return Paths;
}

bool AFacilityHallEncounter::IsMedicalBossDefeated() const
{
    return Slots.IsValidIndex(MedicalBossSlot) && Slots[MedicalBossSlot].bDefeated;
}

void AFacilityHallEncounter::ConfigureMedical()
{
    for (const FString& Path : MedicalMonsterClassPaths())
    {
        UClass* Class = FSoftClassPath(Path).ResolveClass();
        if (!Class || !Class->IsChildOf(ACharacter::StaticClass()))
        { UE_LOG(LogTemp, Error, TEXT("[MedicalEncounter] Missing prepared class %s"), *Path); return; }
        Members.Add(Class);
    }
    const uint32 Salt = Run->NodeRandomSalt(Room.Id);
    FRandomStream Composition(int32(HashCombineFast(uint32(Run->RunSeed()), DungeonRunDomains::SpawnComposition ^ Salt)));
    Placement.Initialize(int32(HashCombineFast(uint32(Run->RunSeed()), DungeonRunDomains::SpawnPlacement ^ Salt)));
    if (Room.Module == TEXT("MedicalDoctorOffice"))
    {
        // Separate draw preserves the existing staff count/composition stream.
        FRandomStream OfficeDraw=Run->GameplayStream(DungeonRunDomains::SpawnComposition ^ Salt ^ 0x4D4F4646u);
        const int32 First=OfficeDraw.RandRange(0,UE_ARRAY_COUNT(MedicalOfficeRooms)-1);
        int32 Second=OfficeDraw.RandRange(0,UE_ARRAY_COUNT(MedicalOfficeRooms)-2);
        if (Second>=First) ++Second;
        for (int32 Selected:{First,Second})
        { auto& Slot=Slots.AddDefaulted_GetRef(); Slot.Member=3; Slot.MedicalPosition=Selected; }
        UE_LOG(LogTemp,Log,TEXT("[MedicalEncounter] Office mantis rooms=%d,%d (one per room)"),First,Second);
    }
    if (Room.Module == TEXT("AbandonedIsolationWard"))
        for (int32 I=0; I<5; ++I)
        { auto& Slot=Slots.AddDefaulted_GetRef(); Slot.Member=3; Slot.MedicalPosition=I; }
    if (Room.Module == TEXT("AbandonedAnatomyTheatre"))
    {
        MedicalBossSlot=Slots.Num();
        auto& Boss=Slots.AddDefaulted_GetRef(); Boss.Member=5; Boss.bMedicalBoss=true;
        for (int32 I=0; I<2; ++I)
        { auto& Slot=Slots.AddDefaulted_GetRef(); Slot.Member=4; Slot.bCeiling=true; Slot.MedicalPosition=I; }
    }
    const int32 Ordinary=Composition.RandRange(12,15);
    // Guarantee all three staff archetypes in each room, then vary the remainder.
    for (int32 I=0; I<Ordinary; ++I)
    { auto& Slot=Slots.AddDefaulted_GetRef(); Slot.Member=I<3 ? I : Composition.RandRange(0,2); }
    FirstWaveCount=Slots.Num(); bSecondWave=true; // One wave, no service-door reinforcements.
    GetWorldTimerManager().SetTimer(EncounterTimer,this,&AFacilityHallEncounter::UpdateEncounter,.2f,true);
    UE_LOG(LogTemp,Log,TEXT("[MedicalEncounter] %s staff=%d special=%d single_wave=1"),*Room.Module,Ordinary,Slots.Num()-Ordinary);
}

bool AFacilityHallEncounter::FindMedicalSpawn(const FFacilityHallSlot& Slot,const ACharacter* Defaults,FVector& Location,FRotator& Facing)
{
    const FTransform RoomTransform(FRotator(0,Room.Yaw,0),Room.Origin);
    // These are the five authored bedside bays, in the ward's local centimetres.
    static const FBox Bays[] = {
        FBox(FVector(-2000,-1250,4.2),FVector(-400,-450,4.2)),
        FBox(FVector(-400,-1250,4.2),FVector(1200,-450,4.2)),
        FBox(FVector(1200,-1250,4.2),FVector(3000,-450,4.2)),
        FBox(FVector(-3000,450,4.2),FVector(-1000,1250,4.2)),
        FBox(FVector(-1000,450,4.2),FVector(1000,1250,4.2))
    };
    const float Footprint=Slot.bMedicalBoss ? 225.f : Slot.Member==3 ? 65.f : 0.f;
    const double Margin=FMath::Max(Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius(),Footprint)+40.;
    const FBox* MantisRoom=nullptr;
    if (Slot.Member==3)
    {
        if (Room.Module==TEXT("MedicalDoctorOffice") && Slot.MedicalPosition>=0
            && Slot.MedicalPosition<UE_ARRAY_COUNT(MedicalOfficeRooms))
            MantisRoom=&MedicalOfficeRooms[Slot.MedicalPosition];
        else if (Room.Module==TEXT("AbandonedIsolationWard") && Slot.MedicalPosition>=0 && Slot.MedicalPosition<5)
            MantisRoom=&Bays[Slot.MedicalPosition];
        // A placement retry stays in the selected room; it never redraws the
        // pair or falls back to the public corridor or the other mantis' room.
        if (!MantisRoom) return false;
    }
    for (int32 Attempt=0; Attempt<12; ++Attempt)
    {
        FVector Candidate;
        if (MantisRoom)
        {
            const FBox& Bay=*MantisRoom;
            Candidate=RoomTransform.TransformPosition(FVector(Placement.FRandRange(Bay.Min.X+Margin,Bay.Max.X-Margin),
                Placement.FRandRange(Bay.Min.Y+Margin,Bay.Max.Y-Margin),Bay.Min.Z));
        }
        else if (Slot.bCeiling)
        {
            // Separate left/right roof regions, clear of the end door sleeves.
            Candidate=RoomTransform.TransformPosition(FVector(Placement.FRandRange(Slot.MedicalPosition==0 ? -1000. : 300.,
                Slot.MedicalPosition==0 ? -300. : 1000.),Placement.FRandRange(-500.,650.),50.));
        }
        else
        {
            const auto& Cells=Room.WalkCells.IsEmpty() ? Room.Cells : Room.WalkCells;
            if (Cells.IsEmpty()) return false;
            const FBox& Floor=Cells[Placement.RandRange(0,Cells.Num()-1)];
            if (Floor.GetSize().X<=2*Margin || Floor.GetSize().Y<=2*Margin) continue;
            Candidate=FVector(Placement.FRandRange(Floor.Min.X+Margin,Floor.Max.X-Margin),
                Placement.FRandRange(Floor.Min.Y+Margin,Floor.Max.Y-Margin),Room.Origin.Z);
        }
        bool Occupied=false;
        for (auto It=GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (const APawn* Player=It->Get() ? It->Get()->GetPawn().Get() : nullptr)
                Occupied |= FVector::DistSquared2D(Player->GetActorLocation(),Candidate)<FMath::Square(450.);
        for (const auto& Other:Slots)
            if (Other.Monster.IsValid() && (Slot.bCeiling==Other.bCeiling))
                Occupied |= FVector::DistSquared2D(Other.Monster->GetActorLocation(),Candidate)
                    < FMath::Square(Slot.bCeiling ? 550. : FMath::Max(160.,double(Footprint)+100.));
        if (Occupied) continue;
        if (Slot.bCeiling)
        {
            FVector Contact; AM09CeilingRoute* Route=nullptr;
            if (!AM09CeilingRoute::FindPlacement(GetWorld(),Candidate,this,Contact,Route)
                || Room.DistanceSquared(Contact)>FMath::Square(20.)) continue;
            Location=Contact-FVector(0,0,143);
        }
        else if (!FindSpawn(Defaults,Candidate,Location,Footprint)) continue;
        Facing=FRotator(0,Placement.FRandRange(-180.f,180.f),0); return true;
    }
    return false;
}
