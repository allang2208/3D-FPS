#include "FacilityHallEncounter.h"
#include "FacilityHallSpawnSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonThemeEncounter.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/BellowSacLobber.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/HumanoidKnockdownComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "NavigationData.h"
#include "NavigationSystem.h"
#include "TimerManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
constexpr int32 StaffClassCount = 3;
constexpr int32 BellowCount = 4;
}

AFacilityHallEncounter::AFacilityHallEncounter()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
}

bool AFacilityHallEncounter::IsHall(const FString& Module)
{
    return Module == TEXT("FacilityReceptionHall") || Module == TEXT("FacilityTransit");
}

bool AFacilityHallEncounter::IsDoorLeaf(const FString& Module, const FString& Mesh)
{
    return IsHall(Module) && (Mesh.EndsWith(TEXT("/SM_Entry_DoorLeaf"))
        || Mesh.EndsWith(TEXT("/SM_Entry_DoorLeafRight")));
}

TArray<FString> AFacilityHallEncounter::MonsterClassPaths()
{
    return {
        TEXT("/Game/Monsters/FacelessReceptionist/BP_FacelessReceptionist.BP_FacelessReceptionist_C"),
        TEXT("/Game/Monsters/FacelessSecurity/BP_FacelessSecurity.BP_FacelessSecurity_C"),
        TEXT("/Game/Monsters/FacelessResearcher/BP_FacelessResearcher.BP_FacelessResearcher_C"),
        TEXT("/Game/Monsters/BellowSacLobber/BP_BellowSacLobber.BP_BellowSacLobber_C")
    };
}

TArray<FString> AFacilityHallEncounter::PreparationAssetPaths()
{
    TArray<FString> Paths = MonsterClassPaths();
    // All three staff classes use the Nurse knockdown rig. These runtime defaults
    // are not hard references in their blueprints, so loading the classes misses them.
    for (const FSoftObjectPath& Path : UHumanoidKnockdownComponent::DefaultAnimationPaths(TEXT("Nurse")))
        Paths.Add(Path.ToString());
    return Paths;
}

void AFacilityHallEncounter::Configure(UDungeonRunSubsystem* InRun, int32 InNode, AAuthoredDungeonGenerator* InGenerator, ADungeonThemeEncounter* InTheme)
{
    if (!HasAuthority() || !InRun || !InGenerator) return;
    const auto* Node = InRun->NodeById(InNode);
    if (!Node || !IsHall(Node->Module)) return;
    Run = InRun;
    Generator = InGenerator;
    Theme = InTheme;
    InGenerator->OnDestroyed.AddDynamic(this, &AFacilityHallEncounter::DungeonDestroyed);
    Room = *Node;
    // Loaded by the generator's existing asynchronous preparation stage.
    for (const FString& Path : MonsterClassPaths())
    {
        UClass* Class = FSoftClassPath(Path).ResolveClass();
        const UClass* Expected = Members.Num() < StaffClassCount ? ANurseZombie::StaticClass() : ABellowSacLobber::StaticClass();
        if (!Class || !Class->IsChildOf(Expected))
        {
            UE_LOG(LogTemp, Error, TEXT("[HallWaves] Missing prepared monster class: %s"), *Path);
            return;
        }
        Members.Add(Class);
    }
    const FName RoomTag(*FString::Printf(TEXT("DungeonModule.%d.%s"), Room.Id, *Room.Module));
    const FString Prefix = TEXT("DungeonHallDoor.");
    // One registration pass per hall; no world scans in the encounter timer.
    for (TActorIterator<AStaticMeshActor> It(GetWorld()); It; ++It)
    {
        if (It->GetOwner() != InGenerator || !It->ActorHasTag(RoomTag)) continue;
        FString Id;
        for (FName Tag : It->Tags)
            if (Tag.ToString().StartsWith(Prefix)) { Id = Tag.ToString().RightChop(Prefix.Len()); break; }
        if (Id.IsEmpty()) continue;
        auto* Door = Doors.FindByPredicate([&Id](const auto& D) { return D.Id == Id; });
        if (!Door) { Door = &Doors.AddDefaulted_GetRef(); Door->Id = Id; }
        const UStaticMesh* Mesh = It->GetStaticMeshComponent()->GetStaticMesh();
        if (Mesh && Mesh->GetName() == TEXT("SM_Entry_DoorLeaf"))
        { Door->Left = *It; Door->ClosedLeft = It->GetActorTransform(); }
        else if (Mesh && Mesh->GetName() == TEXT("SM_Entry_DoorLeafRight"))
        { Door->Right = *It; Door->ClosedRight = It->GetActorTransform(); }
    }
    Doors.RemoveAll([](const auto& D) { return !D.Left.IsValid() || !D.Right.IsValid(); });
    Doors.Sort([](const auto& A, const auto& B) { return A.Id < B.Id; });
    for (auto& Door : Doors)
    {
        Door.FloorCenter = (Door.ClosedLeft.GetLocation() + Door.ClosedRight.GetLocation()) * .5;
        Door.Inward = Door.ClosedLeft.GetRotation().GetForwardVector().GetSafeNormal2D();
    }
    if (Doors.IsEmpty())
    {
        UE_LOG(LogTemp, Error, TEXT("[HallWaves] %s has no complete authored service doors; encounter not started."), *Room.Module);
        return;
    }
    const uint32 Salt = InRun->NodeRandomSalt(Room.Id);
    FRandomStream Composition(int32(HashCombineFast(uint32(InRun->RunSeed()), DungeonRunDomains::SpawnComposition ^ Salt)));
    Placement.Initialize(int32(HashCombineFast(uint32(InRun->RunSeed()), DungeonRunDomains::SpawnPlacement ^ Salt)));
    FirstWaveCount = Composition.RandRange(12, 15) + BellowCount;
    const int32 SecondWaveCount = Composition.RandRange(12, 15);
    Slots.SetNum(FirstWaveCount + SecondWaveCount);
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
    {
        auto& Slot = Slots[Index];
        if (Index < BellowCount)
        {
            Slot.Member = StaffClassCount;
            Slot.BellowPosition = Index;
        }
        else Slot.Member = Composition.RandRange(0, StaffClassCount - 1);
    }
    GetWorldTimerManager().SetTimer(EncounterTimer, this, &AFacilityHallEncounter::UpdateEncounter, .2f, true);
    UE_LOG(LogTemp, Log, TEXT("[HallWaves] %s: wave1=%d (staff + 2 ground / 2 upper Bellow) wave2=%d staff trigger=%d kills service_doors=%d"),
        *Room.Module, FirstWaveCount, SecondWaveCount, FirstWaveCount / 2 + 1, Doors.Num());
}

APawn* AFacilityHallEncounter::PlayerInHall() const
{
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APawn* Pawn = It->Get() ? It->Get()->GetPawn().Get() : nullptr;
        if (!IsValid(Pawn) || Room.DistanceSquared(Pawn->GetActorLocation()) > FMath::Square(20.)) continue;
        const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        if (!Health || !Health->IsDead()) return Pawn;
    }
    return nullptr;
}

bool AFacilityHallEncounter::FindSpawn(const ACharacter* Defaults, const FVector& Candidate, FVector& Location) const
{
    const auto* Capsule = Defaults->GetCapsuleComponent();
    const auto* Movement = Defaults->GetCharacterMovement();
    const float Radius = Capsule->GetScaledCapsuleRadius(), HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    FNavAgentProperties Agent = Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius = Movement->ShouldUpdateNavAgentWithOwnersCollision() ? Radius : FMath::Max(Agent.AgentRadius, Radius);
    Agent.AgentHeight = Movement->ShouldUpdateNavAgentWithOwnersCollision() ? HalfHeight * 2.f : FMath::Max(Agent.AgentHeight, HalfHeight * 2.f);
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const ANavigationData* Data = Nav ? Nav->GetNavDataForProps(Agent, Candidate) : nullptr;
    if (!Data || Data->GetConfig().AgentRadius + KINDA_SMALL_NUMBER < Agent.AgentRadius
        || Data->GetConfig().AgentHeight + KINDA_SMALL_NUMBER < Agent.AgentHeight) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FacilityHallSpawn), false, this);
    FHitResult Ground;
    if (!GetWorld()->LineTraceSingleByChannel(Ground, Candidate + FVector(0,0,100), Candidate - FVector(0,0,100), ECC_Pawn, Query)
        || Ground.ImpactNormal.Z < FMath::Max(.72f, Movement->GetWalkableFloorZ())
        || FMath::Abs(Ground.ImpactPoint.Z - Candidate.Z) > 40.
        || (Ground.GetActor() && Ground.GetActor()->IsA<APawn>()) || !Room.AllowsSpawn(Ground.ImpactPoint)) return false;
    FNavLocation Projected;
    if (!Nav->ProjectPointToNavigation(Ground.ImpactPoint, Projected, FVector(20,20,60), Data)
        || FVector::DistSquared2D(Projected.Location, Ground.ImpactPoint) > FMath::Square(20.)
        || FMath::Abs(Projected.Location.Z - Ground.ImpactPoint.Z) > 40.) return false;
    Location = Ground.ImpactPoint + FVector(0,0,HalfHeight + 3.f);
    if (GetWorld()->OverlapBlockingTestByChannel(Location, FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeCapsule(Radius + 3.f, HalfHeight), Query)) return false;
    for (const FVector Offset : { FVector(Radius,0,0), FVector(-Radius,0,0), FVector(0,Radius,0), FVector(0,-Radius,0) })
    {
        FHitResult Edge;
        const FVector Probe = Ground.ImpactPoint + Offset;
        if (!GetWorld()->LineTraceSingleByChannel(Edge, Probe + FVector(0,0,40), Probe - FVector(0,0,50), ECC_Pawn, Query)
            || Edge.ImpactNormal.Z < Movement->GetWalkableFloorZ() || FMath::Abs(Edge.ImpactPoint.Z - Ground.ImpactPoint.Z) > 30.f
            || (Edge.GetActor() && Edge.GetActor()->IsA<APawn>())) return false;
    }
    return true;
}

bool AFacilityHallEncounter::FindInitialSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing)
{
    const bool Bellow = Slot.BellowPosition != INDEX_NONE;
    const bool Upper = Slot.BellowPosition >= 2;
    const bool Reception = Room.Module == TEXT("FacilityReceptionHall");
    const FTransform HallTransform(FRotator(0, Room.Yaw, 0), Room.Origin);
    const auto& Cells = Room.WalkCells.IsEmpty() ? Room.Cells : Room.WalkCells;
    // Ground-floor staff and Bellow share the main hall, excluding connector sleeves.
    FBox Floor = Room.Volume;
    double Area = 0.;
    for (const FBox& Cell : Cells)
    {
        const FVector Size = Cell.GetSize();
        if (Size.X * Size.Y > Area) { Area = Size.X * Size.Y; Floor = Cell; }
    }
    if (Upper)
    {
        // Authoring contracts: reception's two open side galleries at 450 cm;
        // transit's west platform ends at 420 cm, outside the enclosed duty room.
        // These boxes are local to the module, not unrotated world coordinates.
        const bool PositiveSide = Slot.BellowPosition == 3;
        Floor = Reception
            ? FBox(FVector(-1600, PositiveSide ? 1050 : -1650, 450), FVector(1400, PositiveSide ? 1650 : -1050, 450))
            : FBox(FVector(-2400, PositiveSide ? 1050 : -1800, 420), FVector(-1600, PositiveSide ? 1800 : -1050, 420));
    }
    const double Margin = Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius() + 80.;
    for (int32 Attempt = 0; Attempt < 12; ++Attempt)
    {
        FVector Candidate(Placement.FRandRange(Floor.Min.X + Margin, Floor.Max.X - Margin),
            Placement.FRandRange(Floor.Min.Y + Margin, Floor.Max.Y - Margin), Upper ? Floor.Min.Z : Room.Origin.Z);
        if (Upper) Candidate = HallTransform.TransformPosition(Candidate);
        bool Occupied = false;
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (It->Get() && It->Get()->GetPawn()
                && FVector::DistSquared(It->Get()->GetPawn()->GetActorLocation(), Candidate) < FMath::Square(450.)) Occupied = true;
        if (Bellow) for (const auto& Other : Slots)
            if (Other.BellowPosition != INDEX_NONE && Other.Monster.IsValid()
                && FVector::DistSquared(Other.Monster->GetActorLocation(), Candidate) < FMath::Square(400.)) Occupied = true;
        // Rejected upstairs positions stay upstairs; never fall back to the atrium floor.
        if (Occupied || !FindSpawn(Defaults, Candidate, Location)) continue;
        Facing = FRotator(0, Placement.FRandRange(-180.f, 180.f), 0);
        if (Upper)
        {
            const FVector Inward = Reception ? FVector(0, Slot.BellowPosition == 3 ? -1 : 1, 0) : FVector::ForwardVector;
            Facing = HallTransform.TransformVectorNoScale(Inward).Rotation();
            Facing.Yaw += Placement.FRandRange(-25.f, 25.f);
        }
        return true;
    }
    return false;
}

bool AFacilityHallEncounter::SpawnSlot(int32 SlotIndex)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHallSpawn_Create);
    auto& Slot = Slots[SlotIndex];
    const auto* Defaults = Members[Slot.Member]->GetDefaultObject<ACharacter>();
    const bool Reinforcement = SlotIndex >= FirstWaveCount;
    FVector Location;
    FRotator Facing;
    FFacilityHallDoor* Exit = nullptr;
    if (Reinforcement)
    {
        for (int32 Attempt = 0; Attempt < Doors.Num(); ++Attempt)
        {
            auto& Door = Doors[(NextDoor + Attempt) % Doors.Num()];
            if (Door.OpenAlpha < .999f || GetWorld()->GetTimeSeconds() < Door.NextSpawnAt) continue;
            // Inside the real 150 cm service recess, behind its authored hinged leaves.
            // Never move a rejected spawn out into the middle of the hall.
            if (!FindSpawn(Defaults, Door.FloorCenter - Door.Inward * 65., Location)) continue;
            Exit = &Door;
            NextDoor = (NextDoor + Attempt + 1) % Doors.Num();
            Facing = Door.Inward.Rotation();
            break;
        }
        if (!Exit) return false;
    }
    else if (!FindInitialSpawn(Slot, Defaults, Location, Facing)) return false;
    const FTransform Transform(Facing, Location);
    auto* Monster = GetWorld()->SpawnActorDeferred<ACharacter>(Members[Slot.Member], Transform, this, nullptr,
        ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding);
    if (!Monster) return false;
    if (auto* Staff = Cast<ANurseZombie>(Monster)) Staff->Rank = EMonsterRank::Normal;
    if (auto* Bellow = Cast<ABellowSacLobber>(Monster)) Bellow->Rank = EMonsterRank::Normal;
    Monster->Tags.AddUnique(Run->EnemySlotTag(Room.Id, SlotIndex));
    Monster->Tags.AddUnique(TEXT("FacilityHallEnemy"));
    if (Slot.BellowPosition != INDEX_NONE)
        Monster->Tags.AddUnique(Slot.BellowPosition >= 2 ? TEXT("FacilityHallBellow.Upper") : TEXT("FacilityHallBellow.Ground"));
    Slot.Monster = Monster;
    Monster->OnTakeAnyDamage.AddDynamic(this, &AFacilityHallEncounter::MonsterDamaged);
    Monster->OnDestroyed.AddDynamic(this, &AFacilityHallEncounter::MonsterDestroyed);
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHallSpawn_FinishSpawning);
        Monster->FinishSpawning(Transform);
    }
    if (!IsValid(Monster)) return false;
    if (!Monster->GetController()) Monster->SpawnDefaultController();
    if (Exit)
    {
        // Existing return-home BT moves an entrant out even if the player has left.
        if (auto* Staff = Cast<ANurseZombie>(Monster))
            Staff->SpawnPosition = Exit->FloorCenter + Exit->Inward * 250. + FVector(0,0,Monster->GetSimpleCollisionHalfHeight());
        Exit->NextSpawnAt = GetWorld()->GetTimeSeconds() + 1.;
    }
    if (auto* AI = Cast<AMonsterAIController>(Monster->GetController()))
    {
        AI->SetEncounterArea(Theme.Get());
        AI->UpdateKnowledge();
    }
    return true;
}

void AFacilityHallEncounter::RecordDefeat(AActor* Actor)
{
    if (bStopping || !Actor) return;
    const auto* Combat = Actor->FindComponentByClass<UMonsterCombatComponent>();
    float Health = 0.f, MaxHealth = 0.f;
    FText Name;
    // Both staff and Bellow update health before broadcasting OnTakeAnyDamage;
    // their death-state enums may still be transitioning inside that callback.
    if (!Combat || !Combat->GetVitals(Health, MaxHealth, Name) || Health > 0.f) return;
    for (int32 Index = 0; Index < Slots.Num(); ++Index)
    {
        auto& Slot = Slots[Index];
        if (Slot.Monster.Get() != Actor || Slot.bDefeated) continue;
        Slot.bDefeated = true;
        if (Index < FirstWaveCount) ++FirstWaveKills;
        if (!bSecondWave && FirstWaveKills * 2 > FirstWaveCount)
        {
            bSecondWave = true;
            UE_LOG(LogTemp, Log, TEXT("[HallWaves] %s wave2 triggered: killed=%d/%d count=%d"),
                *Room.Module, FirstWaveKills, FirstWaveCount, Slots.Num() - FirstWaveCount);
        }
        return;
    }
}

void AFacilityHallEncounter::MonsterDamaged(AActor* Actor, float, const UDamageType*, AController*, AActor*)
{
    // Species health is authoritative before Super::TakeDamage broadcasts this event.
    // Schedule on the timer; never spawn or commit profile state inside the damage stack.
    RecordDefeat(Actor);
}

void AFacilityHallEncounter::MonsterDestroyed(AActor* Actor)
{
    if (bStopping) return;
    RecordDefeat(Actor);
    for (auto& Slot : Slots)
        if (Slot.Monster.Get() == Actor) { Slot.Monster.Reset(); break; }
    // Non-lethal deletion leaves the same slot pending, never counts as a kill.
}

void AFacilityHallEncounter::DungeonDestroyed(AActor*)
{
    Destroy();
}

bool AFacilityHallEncounter::DoorOccupied(const FFacilityHallDoor& Door) const
{
    FCollisionObjectQueryParams Pawns(ECC_Pawn);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FacilityHallDoor), false, this);
    return GetWorld()->OverlapAnyTestByObjectType(Door.FloorCenter - Door.Inward * 20. + FVector(0,0,140),
        Door.Inward.Rotation().Quaternion(), Pawns, FCollisionShape::MakeBox(FVector(150,105,140)), Query);
}

void AFacilityHallEncounter::ApplyDoorPose(FFacilityHallDoor& Door)
{
    // Ease the complete open/close motion; each leaf rotates around its real hinge.
    const float A = FMath::SmoothStep(0.f, 1.f, Door.OpenAlpha);
    if (Door.Left.IsValid()) Door.Left->SetActorRotation(Door.ClosedLeft.GetRotation() * FQuat(FVector::UpVector, FMath::DegreesToRadians(85.f * A)));
    if (Door.Right.IsValid()) Door.Right->SetActorRotation(Door.ClosedRight.GetRotation() * FQuat(FVector::UpVector, FMath::DegreesToRadians(-85.f * A)));
}

void AFacilityHallEncounter::Tick(float Dt)
{
    Super::Tick(Dt);
    bool Moving = false;
    for (auto& Door : Doors)
    {
        const float Target = Door.bWantOpen ? 1.f : 0.f;
        if (Door.OpenAlpha == Target) continue;
        if (!Door.bWantOpen && DoorOccupied(Door)) { Moving = true; continue; }
        Door.OpenAlpha = FMath::FInterpConstantTo(Door.OpenAlpha, Target, Dt, 1.f / .7f);
        ApplyDoorPose(Door);
        Moving |= Door.OpenAlpha != Target;
    }
    SetActorTickEnabled(Moving);
}

void AFacilityHallEncounter::UpdateEncounter()
{
    if (bStopping) return;
    if (!Run.IsValid() || !Run->IsRunActive() || !Generator.IsValid()) { Destroy(); return; }
    if (Generator->IsPreparationPending() || !Theme.IsValid() || !Theme->HasStarted()) return;
    // Sealing an area starts its waves, not omniscient aggro. Each monster
    // acquires through sight/damage or investigates a nearby ally's warning.
    if (PlayerInHall()) Run->MarkRoomExplored(Room.Id);
    // Death delegates handle the normal path; this also observes non-damage death transitions.
    for (auto& Slot : Slots)
        if (!Slot.bDefeated && Slot.Monster.IsValid()) RecordDefeat(Slot.Monster.Get());
    bool PendingReinforcements = false;
    for (int32 Index = FirstWaveCount; Index < Slots.Num(); ++Index)
        PendingReinforcements |= !Slots[Index].bDefeated && !Slots[Index].Monster.IsValid();
    for (auto& Door : Doors)
    {
        const bool WantOpen = bSecondWave && PendingReinforcements;
        if (Door.bWantOpen != WantOpen)
        { Door.bWantOpen = WantOpen; SetActorTickEnabled(true); }
    }
    // Keep per-hall cadence and composition; a world queue separates halls which
    // otherwise fire on the same frame and accumulate render registration work.
    const int32 Eligible = bSecondWave ? Slots.Num() : FirstWaveCount;
    for (int32 Index = 0; Index < Eligible; ++Index)
        if (!Slots[Index].bDefeated && !Slots[Index].Monster.IsValid())
        {
            GetWorld()->GetSubsystem<UFacilityHallSpawnSubsystem>()->Request(this);
            break;
        }
    if (!bCleared && bSecondWave && !Slots.ContainsByPredicate([](const auto& S) { return !S.bDefeated; }))
    {
        bCleared = true;
        Run->MarkRoomCleared(Room.Id);
        GetWorldTimerManager().ClearTimer(EncounterTimer);
        UE_LOG(LogTemp, Log, TEXT("[HallWaves] %s cleared: two waves, %d kills"), *Room.Module, Slots.Num());
    }
}

bool AFacilityHallEncounter::TrySpawnPendingSlot()
{
    // Requests can outlive a theme/run transition. Recheck ownership before any
    // placement RNG, navigation query, actor construction or AI activation.
    if (bStopping || bCleared || !HasAuthority() || !Run.IsValid() || !Run->IsRunActive()
        || !Generator.IsValid() || Generator->IsPreparationPending() || !Theme.IsValid() || !Theme->HasStarted()) return false;
    const int32 Eligible = bSecondWave ? Slots.Num() : FirstWaveCount;
    for (int32 Offset = 0; Offset < Eligible; ++Offset)
    {
        const int32 Index = (NextSlot + Offset) % Eligible;
        if (!Slots[Index].bDefeated && !Slots[Index].Monster.IsValid())
        {
            // One bounded attempt per admission. A blocked balcony must not
            // starve the ground-floor slots or service-door reinforcements.
            NextSlot = (Index + 1) % Eligible;
            return SpawnSlot(Index);
        }
    }
    return false;
}

void AFacilityHallEncounter::EndPlay(const EEndPlayReason::Type Reason)
{
    bStopping = true;
    if (auto* Scheduler = GetWorld()->GetSubsystem<UFacilityHallSpawnSubsystem>()) Scheduler->Cancel(this);
    GetWorldTimerManager().ClearTimer(EncounterTimer);
    if (Generator.IsValid()) Generator->OnDestroyed.RemoveDynamic(this, &AFacilityHallEncounter::DungeonDestroyed);
    for (auto& Slot : Slots)
        if (auto* Monster = Slot.Monster.Get())
        {
            Monster->OnTakeAnyDamage.RemoveDynamic(this, &AFacilityHallEncounter::MonsterDamaged);
            Monster->OnDestroyed.RemoveDynamic(this, &AFacilityHallEncounter::MonsterDestroyed);
            Monster->Destroy();
        }
    for (auto& Door : Doors)
    {
        if (Door.Left.IsValid()) Door.Left->SetActorTransform(Door.ClosedLeft);
        if (Door.Right.IsValid()) Door.Right->SetActorTransform(Door.ClosedRight);
    }
    Super::EndPlay(Reason);
}
