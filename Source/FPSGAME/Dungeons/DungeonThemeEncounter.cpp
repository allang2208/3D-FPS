#include "DungeonThemeEncounter.h"
#include "DungeonRunSubsystem.h"
#include "DungeonRoomGate.h"
#include "DungeonRoomGateDimensions.h"
#include "AuthoredDungeonGenerator.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"

ADungeonThemeEncounter::ADungeonThemeEncounter()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
}

bool ADungeonThemeEncounter::Configure(UDungeonRunSubsystem* InRun, AAuthoredDungeonGenerator* InGenerator,
    const TArray<int32>& InRooms, const TArray<FDungeonRunDoor>& Exits)
{
    if (!HasAuthority() || !InRun || !InGenerator || InRooms.IsEmpty() || Exits.IsEmpty()) return false;
    Run = InRun; Generator = InGenerator; Rooms = InRooms;
    InGenerator->OnDestroyed.AddDynamic(this, &ADungeonThemeEncounter::DungeonDestroyed);
    for (const auto& Door : Exits)
    {
        FActorSpawnParameters Params;
        Params.Owner = this; Params.ObjectFlags |= RF_Transient;
        auto* Gate = GetWorld()->SpawnActor<ADungeonRoomGate>(ADungeonRoomGate::StaticClass(), FTransform::Identity, Params);
        if (!Gate) return false;
        Gates.Add(Gate);
        if (!Gate->Configure(Door)) return false;
        Gate->Tags.AddUnique(TEXT("DungeonTheme.Exit"));
    }
    GetWorldTimerManager().SetTimer(EncounterTimer, this, &ADungeonThemeEncounter::UpdateEncounter, .1f, true);
    UE_LOG(LogTemp, Log, TEXT("[DungeonTheme] Area prepared: rooms=%d exits=%d"), Rooms.Num(), Gates.Num());
    return true;
}

bool ADungeonThemeEncounter::ContainsLocation(const FVector& Location) const
{
    if (!Run.IsValid()) return false;
    for (int32 Id : Rooms)
        if (const auto* Room = Run->NodeById(Id); Room && Room->DistanceSquared(Location) <= FMath::Square(20.)) return true;
    return false;
}

APawn* ADungeonThemeEncounter::PlayerInArea() const
{
    if (!Run.IsValid()) return nullptr;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Player = It->Get() ? It->Get()->GetPawn().Get() : nullptr;
        if (!IsValid(Player)) continue;
        const auto* Health = Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if (Health && Health->IsDead()) continue;
        if (ContainsLocation(Player->GetActorLocation())) return Player;
    }
    return nullptr;
}

void ADungeonThemeEncounter::UpdateEncounter()
{
    if (!Run.IsValid() || !Run->IsRunActive() || !Generator.IsValid()) { Destroy(); return; }
    if (Generator->IsPreparationPending()) return;
    if (!bStarted)
    {
        if (!PlayerInArea()) return;
        // Reserve every player's capsule at an exit before beginning the fight.
        // Normally entry is in the reception hall, far from these three exits.
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (APawn* Player = It->Get() ? It->Get()->GetPawn().Get() : nullptr)
                for (const ADungeonRoomGate* Gate : Gates) if (Gate->IsSweepOccupied(Player)) return;
        bStarted = true;
        for (ADungeonRoomGate* Gate : Gates) Gate->SetEncounterLocked(true);
        SetActorTickEnabled(true);
        UE_LOG(LogTemp, Log, TEXT("[DungeonTheme] Area entered: locked %d exits; all %d rooms required"), Gates.Num(), Rooms.Num());
    }
    // A room is clear only after its full composition, including pending wave 2,
    // has actually died. Leaving/dying and a single clear room never release us.
    for (int32 Id : Rooms) if (!Run->IsRoomCleared(Id)) return;
    bCleared = true;
    GetWorldTimerManager().ClearTimer(EncounterTimer);
    SetActorTickEnabled(true);
    UE_LOG(LogTemp, Log, TEXT("[DungeonTheme] Entire area cleared: opening %d exits"), Gates.Num());
}

void ADungeonThemeEncounter::Tick(float Dt)
{
    Super::Tick(Dt);
    const float Target = bCleared ? 1.f : 0.f;
    OpenFraction = FMath::FInterpConstantTo(OpenFraction, Target, Dt, 1.f / float(DungeonRoomGateDimensions::TravelSeconds));
    for (ADungeonRoomGate* Gate : Gates) Gate->SetOpenFraction(OpenFraction);
    if (OpenFraction == Target)
    {
        // Keep the full doorway locked throughout the lift; release together
        // only once the real panels have cleared all three openings.
        if (bCleared) for (ADungeonRoomGate* Gate : Gates) Gate->SetEncounterLocked(false);
        SetActorTickEnabled(false);
    }
}

void ADungeonThemeEncounter::DungeonDestroyed(AActor*) { Destroy(); }

void ADungeonThemeEncounter::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(EncounterTimer);
    if (Generator.IsValid()) Generator->OnDestroyed.RemoveDynamic(this, &ADungeonThemeEncounter::DungeonDestroyed);
    for (ADungeonRoomGate* Gate : Gates) if (IsValid(Gate)) Gate->Destroy();
    Gates.Reset();
    Super::EndPlay(Reason);
}
