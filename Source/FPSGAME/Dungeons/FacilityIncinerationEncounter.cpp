#include "FacilityHallEncounter.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HundredEyedSlagMonster.h"
#include "../Monsters/MantisM27Monster.h"
#include "../Monsters/M66IncineratorMonster.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace
{
constexpr int32 Technician=0, Porter=1, Slag=2, Mantis=3, M66=4;
float IncinerationFootprint(int32 Member) { return Member==M66 ? 225.f : Member==Slag ? 100.f : Member==Mantis ? 65.f : 44.f; }
const FVector HallSlags[]={FVector(-650,-140,5),FVector(650,-140,5)};
const FVector BasementSpawns[]={FVector(-500,300,-355),FVector(500,300,-355),FVector(-500,-300,-355),FVector(450,-300,-355)};
// All three are on the central ground aisle, ahead of the z=240 rear platform.
const FVector FlueSpawns[]={FVector(0,420,5),FVector(0,-180,5),FVector(0,-600,5)};
}

bool AFacilityHallEncounter::IsIncineration(const FString& Module)
{ return Module==TEXT("ShoredBreach") || Module==TEXT("AbandonedIncineratorHall") || Module==TEXT("AbandonedFlueGasStation"); }

TArray<FString> AFacilityHallEncounter::IncinerationMonsterClassPaths()
{
    return {
        TEXT("/Game/Monsters/CargoTechnician/BP_CargoTechnician.BP_CargoTechnician_C"),
        TEXT("/Game/Monsters/CargoPorter/BP_CargoPorter.BP_CargoPorter_C"),
        TEXT("/Script/FPSGAME.HundredEyedSlagMonster"),
        TEXT("/Game/Monsters/MantisM27/BP_MantisM27.BP_MantisM27_C"),
        TEXT("/Game/Monsters/IncineratorBossM66/BP_M66RigPreview.BP_M66RigPreview_C")};
}

bool AFacilityHallEncounter::IsIncinerationBossDefeated() const
{ return Slots.IsValidIndex(IncinerationBossSlot) && Slots[IncinerationBossSlot].bDefeated; }

void AFacilityHallEncounter::ConfigureIncineration()
{
    const UClass* Expected[]={ANurseZombie::StaticClass(),ANurseZombie::StaticClass(),AHundredEyedSlagMonster::StaticClass(),AMantisM27Monster::StaticClass(),AM66IncineratorMonster::StaticClass()};
    for (const FString& Path:IncinerationMonsterClassPaths())
    {
        UClass* Class=FSoftClassPath(Path).ResolveClass();
        if (!Class || !Class->IsChildOf(Expected[Members.Num()]))
        { UE_LOG(LogTemp,Error,TEXT("[IncinerationEncounter] Missing prepared class %s"),*Path); return; }
        Members.Add(Class);
    }
    const uint32 Salt=Run->NodeRandomSalt(Room.Id);
    FRandomStream Composition(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnComposition ^ Salt)));
    Placement.Initialize(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnPlacement ^ Salt)));
    const bool Hall=Room.Module==TEXT("AbandonedIncineratorHall"),Flue=Room.Module==TEXT("AbandonedFlueGasStation");
    if (Flue)
    {
        IncinerationBossSlot=Slots.Num();auto& Boss=Slots.AddDefaulted_GetRef();
        Boss.Member=M66;Boss.bIncinerationBoss=true;Boss.IncinerationPosition=0;
    }
    if (Hall || Flue) for (int32 I=0;I<2;++I)
    { auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=Slag;Slot.IncinerationPosition=Flue ? I+1 : I; }
    const int32 StaffCount=Flue ? 0 : Composition.RandRange(6,8);
    for (int32 I=0;I<StaffCount;++I)
    {
        auto& Slot=Slots.AddDefaulted_GetRef();
        Slot.Member=I<2 ? I : Composition.RandRange(Technician,Porter);
    }
    if (Hall) for (int32 I=0;I<4;++I)
    {
        auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=I<2 ? Slag : Mantis;
        Slot.IncinerationPosition=I;Slot.bIncinerationBasement=true;
    }
    FirstWaveCount=Slots.Num();bSecondWave=true;
    GetWorldTimerManager().SetTimer(EncounterTimer,this,&AFacilityHallEncounter::UpdateEncounter,.2f,true);
    UE_LOG(LogTemp,Log,TEXT("[IncinerationEncounter] room=%s staff=%d ground_slags=%d basement=%d m66=%d"),*Room.Module,StaffCount,(Hall||Flue)?2:0,Hall?4:0,Flue?1:0);
}

void AFacilityHallEncounter::UpdateIncinerationBasement()
{
    if (bIncinerationBasementEntered || Room.Module!=TEXT("AbandonedIncineratorHall") || !HasAuthority())return;
    const FTransform Transform(FRotator(0,Room.Yaw,0),Room.Origin);
    for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        const APawn* Player=It->Get() ? It->Get()->GetPawn().Get() : nullptr;
        if (!IsValid(Player))continue;
        const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if (Health && Health->IsDead())continue;
        const FVector Feet=Player->GetNavAgentLocation(),Local=Transform.InverseTransformPosition(Feet);
        // B1 floor is -360 cm. Trigger on the final stair approach/actual B1,
        // not on a ground-floor capsule over the stair opening or nearby room.
        if (Local.Z> -300. || Local.Z< -400. || Local.X< -1360. || Local.X>1360.
            || Local.Y< -1030. || Local.Y>1030. || Room.DistanceSquared(Feet)>FMath::Square(20.))continue;
        bIncinerationBasementEntered=true;
        UE_LOG(LogTemp,Log,TEXT("[IncinerationEncounter] basement entered: room=%d player=%s; releasing two Slag and two Mantis slots"),Room.Id,*Player->GetName());
        return;
    }
}

bool AFacilityHallEncounter::FindIncinerationSpawn(const FFacilityHallSlot& Slot,const ACharacter* Defaults,FVector& Location,FRotator& Facing)
{
    const FTransform Transform(FRotator(0,Room.Yaw,0),Room.Origin);
    const bool Hall=Room.Module==TEXT("AbandonedIncineratorHall"),Flue=Room.Module==TEXT("AbandonedFlueGasStation");
    const float Radius=FMath::Max(IncinerationFootprint(Slot.Member),Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius());
    for (int32 Attempt=0;Attempt<12;++Attempt)
    {
        FVector Candidate;
        if (Slot.IncinerationPosition!=INDEX_NONE)
        {
            FVector Local=Slot.bIncinerationBasement ? BasementSpawns[Slot.IncinerationPosition]
                : Flue ? FlueSpawns[Slot.IncinerationPosition] : HallSlags[Slot.IncinerationPosition];
            if (Attempt>0)Local+=FVector(Placement.FRandRange(-100.f,100.f),Placement.FRandRange(-70.f,70.f),0);
            Candidate=Transform.TransformPosition(Local);
        }
        else if (Hall)
        {
            const float Margin=Radius+35.f;
            Candidate=Transform.TransformPosition(FVector(Placement.FRandRange(-1360.f+Margin,1360.f-Margin),
                Placement.FRandRange(-470.f+Margin,225.f-Margin),5.f));
        }
        else
        {
            // ShoredBreach has several rotated author cells. Actual ground,
            // collision and navigation below still decide valid placement.
            const auto& Cells=Room.WalkCells.IsEmpty() ? Room.Cells : Room.WalkCells;
            if (Cells.IsEmpty())return false;
            const FBox& Cell=Cells[Placement.RandRange(0,Cells.Num()-1)];const double Margin=Radius+35.;
            if (Cell.GetSize().X<=2*Margin || Cell.GetSize().Y<=2*Margin)continue;
            Candidate=FVector(Placement.FRandRange(Cell.Min.X+Margin,Cell.Max.X-Margin),
                Placement.FRandRange(Cell.Min.Y+Margin,Cell.Max.Y-Margin),Room.Origin.Z+5.);
        }
        bool Occupied=false;
        for (auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if (const APawn* Player=It->Get() ? It->Get()->GetPawn().Get() : nullptr)
                Occupied |= FMath::Abs(Player->GetNavAgentLocation().Z-Candidate.Z)<180.
                    && FVector::DistSquared2D(Player->GetActorLocation(),Candidate)<FMath::Square(Slot.bIncinerationBoss ? 600. : 350.);
        for (const auto& Other:Slots)if (Other.Monster.IsValid())
            Occupied |= FMath::Abs(Other.Monster->GetNavAgentLocation().Z-Candidate.Z)<120.
                && FVector::DistSquared2D(Other.Monster->GetActorLocation(),Candidate)<FMath::Square(Radius+IncinerationFootprint(Other.Member)+65.f);
        if (Occupied || !FindSpawn(Defaults,Candidate,Location,Radius))continue;
        Facing=FRotator(0,Room.Yaw+(Flue ? -90.f : Placement.FRandRange(-180.f,180.f)),0);
        return true;
    }
    return false; // Keep this exact slot/floor pending; never force overlap or count a failure as death.
}
