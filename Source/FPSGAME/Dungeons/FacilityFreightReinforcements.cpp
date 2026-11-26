#include "FacilityHallEncounter.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonThemeEncounter.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "Net/UnrealNetwork.h"

namespace
{
constexpr int32 WorkerLimit=8;
constexpr double WaveSeconds=20.;
constexpr float DoorSeconds=.7f;
}

void AFacilityHallEncounter::BeginPlay()
{
    Super::BeginPlay();
    // Initial replication can arrive before the client's generated room is ready.
    if(GetNetMode()==NM_Client)SetActorTickEnabled(true);
}

void AFacilityHallEncounter::RegisterServiceDoors()
{
    const FName RoomTag(*FString::Printf(TEXT("DungeonModule.%d.%s"),Room.Id,*Room.Module));
    const FString Prefix=TEXT("DungeonFreightDoor.");
    // Registration happens once after assembly, before any encounter timers.
    for(TActorIterator<AStaticMeshActor> It(GetWorld());It;++It)
    {
        if(It->GetOwner()!=Generator.Get()||!It->ActorHasTag(RoomTag))continue;
        FString Id;
        for(const FName Tag:It->Tags)
            if(Tag.ToString().StartsWith(Prefix)){Id=Tag.ToString().RightChop(Prefix.Len());break;}
        if(Id.IsEmpty())continue;
        auto* Door=Doors.FindByPredicate([&Id](const auto& D){return D.Id==Id;});
        if(!Door){Door=&Doors.AddDefaulted_GetRef();Door->Id=Id;}
        const UStaticMesh* Mesh=It->GetStaticMeshComponent()->GetStaticMesh();
        if(Mesh&&Mesh->GetName()==TEXT("SM_Entry_DoorLeaf"))
        {Door->Left=*It;Door->ClosedLeft=It->GetActorTransform();}
        else if(Mesh&&Mesh->GetName()==TEXT("SM_Entry_DoorLeafRight"))
        {Door->Right=*It;Door->ClosedRight=It->GetActorTransform();}
    }
    Doors.RemoveAll([](const auto& D){return !D.Left.IsValid()||!D.Right.IsValid();});
    Doors.Sort([](const auto& A,const auto& B){return A.Id<B.Id;});
    for(auto& Door:Doors)
    {
        Door.FloorCenter=(Door.ClosedLeft.GetLocation()+Door.ClosedRight.GetLocation())*.5;
        Door.Inward=Door.ClosedLeft.GetRotation().GetForwardVector().GetSafeNormal2D();
    }
}

void AFacilityHallEncounter::ConfigureFreightReinforcements()
{
    RegisterServiceDoors();
    if(Doors.Num()!=2)
    {
        UE_LOG(LogTemp,Error,TEXT("[FreightEncounter] Expected two service doors, found %d; initial encounter retained."),Doors.Num());
        return;
    }
    NextFreightRewardSlot=FirstWaveCount;
    for(int32 I=0;I<WorkerLimit;++I)
    {
        auto& Slot=Slots.AddDefaulted_GetRef();
        Slot.FreightDoor=I%2;Slot.bDefeated=true;
    }
    EnableServiceDoorReplication();
}

void AFacilityHallEncounter::EnableServiceDoorReplication()
{
    // Both welcome halls and the station animate generated service doors.
    // Replicate poses against stable geometry names; spawning stays server-only.
    bAlwaysRelevant=true;SetReplicates(true);SetReplicateMovement(false);
    SetNetUpdateFrequency(10.f);
    FreightDoorRunId=Run->RunId();
    PublishFreightDoors();ForceNetUpdate();
}

APawn* AFacilityHallEncounter::FreightTargetNear(const FVector& Location) const
{
    if(!Theme.IsValid())return nullptr;
    APawn* Best=nullptr;double Distance=TNumericLimits<double>::Max();
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        APawn* Player=It->Get()?It->Get()->GetPawn().Get():nullptr;
        if(!Player||!Theme->ContainsLocation(Player->GetActorLocation()))continue;
        const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if(Health&&Health->IsDead())continue;
        const double D=FVector::DistSquared(Location,Player->GetActorLocation());
        if(D<Distance){Best=Player;Distance=D;}
    }
    return Best;
}

void AFacilityHallEncounter::UpdateFreightReinforcements()
{
    if(!HasAuthority()||Doors.Num()!=2||Slots.Num()!=FirstWaveCount+WorkerLimit)return;
    for(int32 I=FirstWaveCount;I<Slots.Num();++I)
    {
        auto& Slot=Slots[I];
        if(Slot.bDefeated||!Slot.Monster.IsValid())continue;
        auto* AI=Cast<AMonsterAIController>(Slot.Monster->GetController());
        if(!AI)continue;
        // The controller may have found an accessible teammate. Keep that lock
        // while it belongs to this room instead of reimposing the nearest pawn.
        APawn* Current=AI->GetEncounterTarget();
        const auto* Health=Current?Current->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        APawn* Target=Current&&Current->IsPlayerControlled()&&(!Health||!Health->IsDead())&&
            Theme.IsValid()&&Theme->ContainsLocation(Current->GetActorLocation())
            ?Current:FreightTargetNear(Slot.Monster->GetActorLocation());
        Slot.FreightTarget=Target;
        if(Target!=Current)AI->SetEncounterTarget(Target);
    }
    if(IsFreightBossDefeated())
    {
        // Pending slots are cancelled, never counted as kills or rewarded.
        for(int32 I=FirstWaveCount;I<Slots.Num();++I)
            if(!Slots[I].Monster.IsValid())Slots[I].bDefeated=true;
        for (int32 I = PreparedMonsters.Num() - 1; I >= 0; --I)
            if (PreparedMonsters[I]->Slot >= FirstWaveCount) DiscardPreparation(I, TEXT("freight_boss_defeated"));
        return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(NextFreightReinforcementsAt<0.){NextFreightReinforcementsAt=Now+WaveSeconds;return;}
    if(Now<NextFreightReinforcementsAt)return;
    NextFreightReinforcementsAt=Now+WaveSeconds;
    if(!FreightTargetNear(Room.Origin))return;
    int32 Active=0;
    for(int32 I=FirstWaveCount;I<Slots.Num();++I)Active+=!Slots[I].bDefeated;
    for(int32 N=0;N<Doors.Num()&&Active<WorkerLimit;++N)
    {
        const int32 DoorIndex=(FreightRound+N)%Doors.Num();
        // A blocked doorway retains one scheduled spawn, not an accumulating queue.
        if(Slots.ContainsByPredicate([DoorIndex](const auto& S)
            {return S.FreightDoor==DoorIndex&&!S.bDefeated&&!S.Monster.IsValid();}))continue;
        int32 Free=INDEX_NONE;
        for(int32 I=FirstWaveCount;I<Slots.Num();++I)if(Slots[I].bDefeated){Free=I;break;}
        if(Free==INDEX_NONE)break;
        if(auto* Retired=Slots[Free].Monster.Get())
        {
            Retired->OnTakeAnyDamage.RemoveDynamic(this,&AFacilityHallEncounter::MonsterDamaged);
            Retired->OnDestroyed.RemoveDynamic(this,&AFacilityHallEncounter::MonsterDestroyed);
        }
        auto& Slot=Slots[Free];Slot={};
        Slot.Member=(FreightRound+DoorIndex)%2; // One porter and one technician per full batch.
        Slot.FreightDoor=DoorIndex;Slot.RewardSlot=NextFreightRewardSlot++;
        ++Active;
    }
    ++FreightRound;
}

void AFacilityHallEncounter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFacilityHallEncounter,FreightDoorRunId);
    DOREPLIFETIME(AFacilityHallEncounter,FreightDoorStates);
}

void AFacilityHallEncounter::PublishFreightDoors()
{
    if(!HasAuthority()||FreightDoorRunId.IsEmpty())return;
    const bool Initial=FreightDoorStates.Num()!=Doors.Num();
    FreightDoorStates.SetNum(Doors.Num());
    bool Urgent=Initial;
    for(int32 I=0;I<Doors.Num();++I)
    {
        const auto& Door=Doors[I];auto& State=FreightDoorStates[I];
        if(!Door.Left.IsValid()||!Door.Right.IsValid())continue;
        const float Target=Door.bWantOpen?1.f:DoorOccupied(Door)?Door.OpenAlpha:0.f;
        if(!Initial&&State.Alpha==Door.OpenAlpha&&State.Target==Target)continue;
        Urgent|=State.Target!=Target||Door.OpenAlpha==Target;
        State.LeftName=Door.Left->GetFName();State.RightName=Door.Right->GetFName();
        State.ClosedLeft=Door.ClosedLeft;State.ClosedRight=Door.ClosedRight;
        State.Alpha=Door.OpenAlpha;State.Target=Target;State.ServerSeconds=GetWorld()->GetTimeSeconds();
    }
    if(Urgent)ForceNetUpdate();
}

void AFacilityHallEncounter::OnRep_FreightDoors()
{
    if(GetNetMode()!=NM_Client)return;
    SetActorTickEnabled(true);PresentFreightDoors();
}

void AFacilityHallEncounter::PresentFreightDoors()
{
    const auto* ClientRun=UDungeonRunSubsystem::Get(GetWorld());
    if(!ClientRun||!ClientRun->IsRunActive()||ClientRun->RunId()!=FreightDoorRunId)
    {SetActorTickEnabled(true);return;}
    const auto* State=GetWorld()->GetGameState();
    const double Now=State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    Doors.SetNum(FreightDoorStates.Num());bool Pending=false;
    for(int32 I=0;I<FreightDoorStates.Num();++I)
    {
        const auto& Net=FreightDoorStates[I];auto& Door=Doors[I];
        if(!Door.Left.IsValid())Door.Left=FindObjectFast<AStaticMeshActor>(GetWorld()->PersistentLevel,Net.LeftName);
        if(!Door.Right.IsValid())Door.Right=FindObjectFast<AStaticMeshActor>(GetWorld()->PersistentLevel,Net.RightName);
        if(!Door.Left.IsValid()||!Door.Right.IsValid()){Pending=true;continue;}
        Door.ClosedLeft=Net.ClosedLeft;Door.ClosedRight=Net.ClosedRight;
        Door.OpenAlpha=FMath::FInterpConstantTo(Net.Alpha,Net.Target,float(FMath::Max(0.,Now-Net.ServerSeconds)),1.f/DoorSeconds);
        ApplyDoorPose(Door);Pending|=Door.OpenAlpha!=Net.Target;
    }
    SetActorTickEnabled(Pending);
}
