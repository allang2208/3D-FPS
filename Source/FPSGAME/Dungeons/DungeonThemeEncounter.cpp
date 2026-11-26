#include "DungeonThemeEncounter.h"
#include "DungeonRunSubsystem.h"
#include "DungeonRoomGate.h"
#include "DungeonRoomGateDimensions.h"
#include "AuthoredDungeonGenerator.h"
#include "FacilityHallEncounter.h"
#include "FacilityHallSpawnSubsystem.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

ADungeonThemeEncounter::ADungeonThemeEncounter()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
}

bool ADungeonThemeEncounter::Configure(UDungeonRunSubsystem* InRun, AAuthoredDungeonGenerator* InGenerator,
    const TArray<int32>& InRooms, const TArray<FDungeonRunDoor>& Boundaries, EDungeonThemeObjective InObjective)
{
    if (!HasAuthority() || !InRun || !InGenerator || InRooms.IsEmpty() || Boundaries.IsEmpty()) return false;
    Run = InRun; Generator = InGenerator; Rooms = InRooms; Objective = InObjective;
    // Cache topology once. Do not prepare a different branch merely because
    // its volume happens to be close through a wall or on another floor.
    if (Objective == EDungeonThemeObjective::WelcomeElite)
    {
        for (const auto& Node : InRun->AllNodes())
            if (Node.Module == TEXT("FacilityEntrancePassage"))
            {
                PreparationApproachNodes.Add(Node.Id);
                SpawnApproachNodes.Add(Node.Id);
            }
        // The fixed entry/shrine space is not a generated run node. Start its
        // optional reservations while players are still there, not only in the
        // short generated passage immediately before the welcome encounter.
        TSharedPtr<FJsonObject> Catalog;
        if (!PreparationApproachNodes.IsEmpty()
            && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(InGenerator->ModuleCatalogJson), Catalog)
            && Catalog.IsValid())
        {
            const auto ReadVector = [&Catalog](const TCHAR* Key, FVector& Out)
            {
                const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
                if (!Catalog->TryGetArrayField(Key, Values) || Values->Num() != 3) return false;
                double Coordinates[3];
                for (int32 I = 0; I < 3; ++I)
                    if (!(*Values)[I].IsValid() || !(*Values)[I]->TryGetNumber(Coordinates[I])) return false;
                Out = FVector(Coordinates[0], Coordinates[1], Coordinates[2]);
                return !Out.ContainsNaN();
            };
            FVector Min, Max;
            if (ReadVector(TEXT("reserved_min"), Min) && ReadVector(TEXT("reserved_max"), Max)
                && Min.X < Max.X && Min.Y < Max.Y && Min.Z < Max.Z)
            {
                const FBox EntryVolume(Min, Max);
                if (EntryVolume.IsInsideOrOn(InRun->EntryPosition())) PreparationStartVolume = EntryVolume;
            }
        }
    }
    else
    {
        TArray<int32> Pending;
        for (int32 Id : Rooms)
            if (const auto* Node = InRun->NodeById(Id))
                for (int32 Neighbor : Node->Neighbors)
                    if (!Rooms.Contains(Neighbor)) Pending.AddUnique(Neighbor);
        for (int32 Index = 0; Index < Pending.Num(); ++Index)
        {
            const auto* Node = InRun->NodeById(Pending[Index]);
            if (!Node || Rooms.Contains(Node->Id)) continue;
            PreparationApproachNodes.AddUnique(Node->Id);
            if (Node->bConnector)
                for (int32 Neighbor : Node->Neighbors)
                    if (!Rooms.Contains(Neighbor)) Pending.AddUnique(Neighbor);
        }
        for (const auto& Door : Boundaries) PreparationEntrances.Add(Door.FloorCenter);

        // Actual spawning starts anywhere along the connected approach passage.
        // Walk only connector nodes from real boundary doors, stopping at rooms
        // and junctions so a nearby/previous room cannot activate another branch.
        TArray<int32> PassageNodes;
        for (const auto& Door : Boundaries) PassageNodes.AddUnique(Door.Neighbor);
        for (int32 Index = 0; Index < PassageNodes.Num(); ++Index)
        {
            const auto* Node = InRun->NodeById(PassageNodes[Index]);
            if (!Node || !Node->bConnector || Rooms.Contains(Node->Id)) continue;
            SpawnApproachNodes.AddUnique(Node->Id);
            for (int32 Neighbor : Node->Neighbors)
                if (!Rooms.Contains(Neighbor)) PassageNodes.AddUnique(Neighbor);
        }
    }
    InGenerator->OnDestroyed.AddDynamic(this, &ADungeonThemeEncounter::DungeonDestroyed);
    for (const auto& Door : Boundaries)
    {
        FActorSpawnParameters Params;
        Params.Owner = this; Params.ObjectFlags |= RF_Transient;
        auto* Gate = GetWorld()->SpawnActor<ADungeonRoomGate>(ADungeonRoomGate::StaticClass(), FTransform::Identity, Params);
        if (!Gate) return false;
        Gates.Add(Gate);
        if (!Gate->Configure(Door)) return false;
        Gate->Tags.AddUnique(UsesBoundaryAdmission() ? TEXT("DungeonTheme.Boundary") : TEXT("DungeonTheme.Exit"));
        if (UsesBoundaryAdmission())
        {
            Gate->SetEntryOnly(true);
            AddTickPrerequisiteActor(Gate);
        }
    }
    GetWorldTimerManager().SetTimer(EncounterTimer, this, &ADungeonThemeEncounter::UpdateEncounter, .1f, true);
    UE_LOG(LogTemp, Log, TEXT("[DungeonTheme] Area prepared: rooms=%d boundaries=%d"), Rooms.Num(), Gates.Num());
    return true;
}

void ADungeonThemeEncounter::RegisterHall(AFacilityHallEncounter* Hall)
{
    if (HasAuthority() && IsValid(Hall) && Hall->GetWorld() == GetWorld()) Halls.AddUnique(Hall);
}

int32 ADungeonThemeEncounter::PreparationPriority(double& DistanceSquared) const
{
    DistanceSquared = PreparationDistanceSquared;
    return PreparationRank;
}

void ADungeonThemeEncounter::UpdatePreparation()
{
    bPlayerOnSpawnApproach = false;
    PreparationRank = INDEX_NONE;
    PreparationDistanceSquared = TNumericLimits<double>::Max();
    if (!Run.IsValid() || !Run->IsRunActive() || !Generator.IsValid() || Generator->IsPreparationPending()) return;
    bool bAlivePlayer = false;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        const APawn* Player = It->Get() ? It->Get()->GetPawn().Get() : nullptr;
        if (!IsValid(Player)) continue;
        const auto* Health = Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if (Health && Health->IsDead()) continue;
        bAlivePlayer = true;
        const FVector At = Player->GetActorLocation();
        if (ContainsLocation(At))
        {
            PreparationRank = 0;
            LastOccupiedAt=GetWorld()->GetTimeSeconds();
            PreparationDistanceSquared = 0.;
            break;
        }
        if (IsSpawnApproachLocation(At))
        {
            bPlayerOnSpawnApproach = true;
            LastOccupiedAt = GetWorld()->GetTimeSeconds();
            PreparationRank = 2;
            double Distance = PreparationEntrances.IsEmpty() ? 0. : TNumericLimits<double>::Max();
            for (const FVector& Entrance : PreparationEntrances)
                Distance = FMath::Min(Distance, FVector::DistSquared(At, Entrance));
            PreparationDistanceSquared = FMath::Min(PreparationDistanceSquared, Distance);
            continue;
        }
        bool bOnApproach = Objective == EDungeonThemeObjective::WelcomeElite && !bStarted
            && PreparationStartVolume.IsValid
            && PreparationStartVolume.ComputeSquaredDistanceToPoint(At) <= FMath::Square(20.);
        for (int32 Id : PreparationApproachNodes)
            if (const auto* Node = Run->NodeById(Id); Node && Node->DistanceSquared(At) <= FMath::Square(20.))
            { bOnApproach = true; break; }
        if (!bOnApproach) continue;
        double Distance = 0.;
        if (Objective != EDungeonThemeObjective::WelcomeElite)
        {
            Distance = TNumericLimits<double>::Max();
            for (const FVector& Entrance : PreparationEntrances)
                Distance = FMath::Min(Distance, FVector::DistSquared(At, Entrance));
            if (Distance > FMath::Square(1800.)) continue;
        }
        PreparationRank = 2;
        PreparationDistanceSquared = FMath::Min(PreparationDistanceSquared, Distance);
    }
    // Crossing a short doorway keeps a brief grace period. A remote, already
    // passed region must not keep preparing/spawning merely because somebody
    // is alive somewhere else in the dungeon.
    if (bStarted && bAlivePlayer && PreparationRank != 0 && !bPlayerOnSpawnApproach && LastOccupiedAt>=0.
        && GetWorld()->GetTimeSeconds()-LastOccupiedAt<=3.) PreparationRank = 1;
    if (PreparationRank == INDEX_NONE) return;
    auto* Scheduler = GetWorld()->GetSubsystem<UFacilityHallSpawnSubsystem>();
    for (const auto& Hall : Halls)
        if (Hall.IsValid()) Scheduler->RequestPreparation(Hall.Get());
}

bool ADungeonThemeEncounter::IsSpawnApproachLocation(const FVector& Location) const
{
    if (!Run.IsValid()) return false;
    for (int32 Id : SpawnApproachNodes)
        if (const auto* Node = Run->NodeById(Id); Node && Node->DistanceSquared(Location) <= FMath::Square(20.)) return true;
    return false;
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
        if (!ContainsLocation(Player->GetActorLocation())) continue;
        // Seal only after one player's whole capsule has crossed a boundary.
        // Other teammates can still be approaching or traversing that doorway.
        if (UsesBoundaryAdmission() && Gates.ContainsByPredicate([Player](const ADungeonRoomGate* Gate)
            { return Gate->IsSweepOccupied(Player); })) continue;
        return Player;
    }
    return nullptr;
}

void ADungeonThemeEncounter::UpdateEncounter()
{
    if (!Run.IsValid() || !Run->IsRunActive() || !Generator.IsValid()) { Destroy(); return; }
    if (bCleared && !Halls.ContainsByPredicate([](const auto& Hall) { return Hall.IsValid() && !Hall->bCleared; }))
    {
        // Once every authored wave is complete there can be no new reservation.
        // Gate opening animation has its own actor tick and must finish normally.
        PreparationRank = INDEX_NONE;
        PreparationDistanceSquared = TNumericLimits<double>::Max();
        GetWorldTimerManager().ClearTimer(EncounterTimer);
        return;
    }
    UpdatePreparation();
    if (Generator->IsPreparationPending()) return;
    if (bCleared) return;
    if (!bStarted)
    {
        if (!bPlayerOnSpawnApproach && !PlayerInArea()) return;
        bStarted = true;
        // One server-owned area event submits every room, including rooms that
        // no player has entered yet. The shared queue still admits one at a time.
        auto* Scheduler = GetWorld()->GetSubsystem<UFacilityHallSpawnSubsystem>();
        for (const auto& Hall : Halls)
            if (Hall.IsValid()) Scheduler->Request(Hall.Get());
        UFPSPerformanceMetricsSubsystem::RecordMarker(this, TEXT("Hall.AreaActivationQueued"),
            FString::Printf(TEXT("objective=%s rooms=%d prepared=%d trigger=%s"), ObjectiveId(), Halls.Num(),
                Scheduler->PreparedCount(), bPlayerOnSpawnApproach ? TEXT("passage") : TEXT("area")), true);
        UE_LOG(LogTemp, Log, TEXT("[DungeonTheme] Spawning started: objective=%s trigger=%s rooms=%d"),
            ObjectiveId(), bPlayerOnSpawnApproach ? TEXT("passage") : TEXT("area"), Halls.Num());
    }
    // Spawning ahead must not seal the doorway in front of the first player.
    // Preserve the existing full-capsule admission and teammate gate behavior.
    if (!bBoundaryActivated && !IsObjectiveDefeated() && PlayerInArea())
    {
        if (!UsesBoundaryAdmission())
            for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
                if (APawn* Player = It->Get() ? It->Get()->GetPawn().Get() : nullptr)
                    for (const ADungeonRoomGate* Gate : Gates) if (Gate->IsSweepOccupied(Player)) return;
        bBoundaryActivated = true;
        for (ADungeonRoomGate* Gate : Gates) Gate->SetEncounterLocked(true);
        SetActorTickEnabled(true);
        UE_LOG(LogTemp, Log, TEXT("[DungeonTheme] Area entered: locked %d boundaries; objective=%s"), Gates.Num(),ObjectiveId());
    }
    // Each region's designated enemy owns passage; surviving ordinary enemies
    // do not keep the onward exits locked or fabricate a room-clear state.
    if (!IsObjectiveDefeated())
    {
        if (bBoundaryActivated && UsesBoundaryAdmission())
            for (const ADungeonRoomGate* Gate : Gates)
                if (Gate->NetOpen != (Gate->WantsInboundOpening() ? 1.f : 0.f))
                { SetActorTickEnabled(true); break; }
        return;
    }
    bCleared = true;
    // Surviving rooms can still have ordinary waves. Keep low-frequency
    // relevance/retirement updates after the objective opens the boundary.
    GetWorldTimerManager().SetTimer(EncounterTimer, this, &ADungeonThemeEncounter::UpdateEncounter, .2f, true);
    SetActorTickEnabled(true);
    UE_LOG(LogTemp, Log, TEXT("[DungeonTheme] Objective defeated: %s; opening %d boundaries"),ObjectiveId(),Gates.Num());
}

bool ADungeonThemeEncounter::IsObjectiveDefeated() const
{
    if (!Run.IsValid()) return false;
    if (Objective==EDungeonThemeObjective::MedicalBoss) return Run->IsMedicalBossDefeated();
    if (Objective==EDungeonThemeObjective::FreightBoss) return Run->IsFreightBossDefeated();
    if (Objective==EDungeonThemeObjective::EcologyBoss) return Run->IsEcologyBossDefeated();
    if (Objective==EDungeonThemeObjective::PowerBoss) return Run->IsPowerBossDefeated();
    if (Objective==EDungeonThemeObjective::IncinerationBoss) return Run->IsIncinerationBossDefeated();
    if (Objective==EDungeonThemeObjective::FinalBoss) return Run->IsFinalBossDefeated();
    if (Objective==EDungeonThemeObjective::StaffLivingBoss) return Run->IsStaffLivingBossDefeated();
    return Run->IsWelcomeEliteDefeated();
}

const TCHAR* ADungeonThemeEncounter::ObjectiveId() const
{
    if (Objective==EDungeonThemeObjective::MedicalBoss) return TEXT("medical.bound_congregate");
    if (Objective==EDungeonThemeObjective::FreightBoss) return TEXT("freight.mawcrawler");
    if (Objective==EDungeonThemeObjective::EcologyBoss) return TEXT("ecology.root_crown");
    if (Objective==EDungeonThemeObjective::PowerBoss) return TEXT("power.vortex_coffer");
    if (Objective==EDungeonThemeObjective::IncinerationBoss) return TEXT("treatment.incinerator_m66");
    if (Objective==EDungeonThemeObjective::FinalBoss) return TEXT("final.heque");
    if (Objective==EDungeonThemeObjective::StaffLivingBoss) return TEXT("staff_living.blind_supplicant");
    return TEXT("welcome.elite");
}

void ADungeonThemeEncounter::Tick(float Dt)
{
    Super::Tick(Dt);
    if (UsesBoundaryAdmission())
    {
        bool bAllSettled = true;
        for (ADungeonRoomGate* Gate : Gates)
        {
            const float Target = bCleared || Gate->WantsInboundOpening() ? 1.f : 0.f;
            const float Fraction = FMath::FInterpConstantTo(Gate->NetOpen, Target, Dt,
                1.f / float(DungeonRoomGateDimensions::TravelSeconds));
            Gate->SetOpenFraction(Fraction);
            bAllSettled &= Fraction == Target;
        }
        if (bAllSettled)
        {
            // An admission only lifts the panels; the directional barrier stays
            // active. The boss releases both barriers together after both lifts.
            if (bCleared) for (ADungeonRoomGate* Gate : Gates) Gate->SetEncounterLocked(false);
            SetActorTickEnabled(false);
        }
        return;
    }
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
