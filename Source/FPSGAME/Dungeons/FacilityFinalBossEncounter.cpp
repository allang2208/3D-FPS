#include "FacilityHallEncounter.h"
#include "../Monsters/HeQueMonster.h"
#include "HeQuePumpControl.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"

bool AFacilityHallEncounter::IsFinalBossRoom(const FString& Module)
{return Module==TEXT("BossPumpHall");}

TArray<FString> AFacilityHallEncounter::FinalBossClassPaths()
{return {TEXT("/Game/Monsters/HeQue/BP_HeQue.BP_HeQue_C")};}

bool AFacilityHallEncounter::IsFinalBossDefeated() const
{return Slots.IsValidIndex(FinalBossSlot)&&Slots[FinalBossSlot].bDefeated;}

void AFacilityHallEncounter::ConfigureFinalBoss()
{
    UClass* Class=FSoftClassPath(FinalBossClassPaths()[0]).ResolveClass();
    if(!Class||!Class->IsChildOf(AHeQueMonster::StaticClass()))
    {UE_LOG(LogTemp,Error,TEXT("[FinalBoss] Prepared HeQue class missing"));return;}
    Members.Add(Class);
    Placement.Initialize(int32(HashCombineFast(uint32(Run->RunSeed()),DungeonRunDomains::SpawnPlacement^Run->NodeRandomSalt(Room.Id))));
    FinalBossSlot=Slots.Num();auto& Slot=Slots.AddDefaulted_GetRef();Slot.Member=0;Slot.bFinalBoss=true;
    FirstWaveCount=1;bSecondWave=true;
    GetWorldTimerManager().SetTimer(EncounterTimer,this,&AFacilityHallEncounter::UpdateEncounter,.2f,true);
}

bool AFacilityHallEncounter::FindFinalBossSpawn(const ACharacter* Defaults,FVector& Location,FRotator& Facing)
{
    const FTransform Frame(FRotator(0,Room.Yaw,0),Room.Origin);
    FVector Origin=Frame.TransformPosition(FVector(0,-1900,0));
    const auto Anchors=Run->RoomAnchors(Room.Id,TEXT("boss_spawn"));
    if(!Anchors.IsEmpty())Origin=Anchors[0]->GetActorLocation();
    for(int32 Attempt=0;Attempt<12;++Attempt)
    {
        const FVector Offset=Attempt==0?FVector::ZeroVector:
            FVector(Placement.FRandRange(-180.f,180.f),Placement.FRandRange(-250.f,300.f),0);
        const FVector Candidate=Origin+Frame.TransformVectorNoScale(Offset);
        bool Occupied=false;
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if(const APawn* Player=It->Get()?It->Get()->GetPawn().Get():nullptr)
                Occupied|=FMath::Abs(Player->GetNavAgentLocation().Z-Candidate.Z)<180.f&&
                    FVector::DistSquared2D(Player->GetActorLocation(),Candidate)<FMath::Square(600.f);
        if(Occupied||!FindSpawn(Defaults,Candidate,Location,225.f))continue;
        Facing=FRotator(0,Room.Yaw+90.f,0);return true;
    }
    // Retry the same objective slot; blocked navigation is never a boss defeat.
    return false;
}

void AFacilityHallEncounter::SpawnPumpControls(AHeQueMonster* Boss)
{
    for(auto& Control:PumpControls)if(Control.IsValid())Control->Destroy();
    PumpControls.Reset();
    if(!IsValid(Boss)||!HasAuthority())return;
    const FTransform Frame(FRotator(0,Room.Yaw,0),Room.Origin);
    // Existing side-platform consoles: deck at 3.6 m, operating wheel at 4.55 m.
    const FVector Mounts[]={FVector(-2504,-2270,455),FVector(2504,-3270,455)};
    // Match the existing ground attack bays below the control platforms: the boss
    // already approaches these when targeting an elevated player, so solo use is viable.
    const FVector Vents[]={FVector(-1850,-2100,0),FVector(1850,-3100,0)};
    for(int32 Side=0;Side<2;++Side)
    {
        const FTransform Local(FRotator(0,Side==0?90.f:-90.f,0),Mounts[Side]);
        FActorSpawnParameters Params;Params.Owner=this;Params.ObjectFlags|=RF_Transient;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        if(auto* Control=GetWorld()->SpawnActor<AHeQuePumpControl>(AHeQuePumpControl::StaticClass(),Local*Frame,Params))
        {Control->Configure(Boss,Frame.TransformPosition(Vents[Side]));PumpControls.Add(Control);}
    }
}
